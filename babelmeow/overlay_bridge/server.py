"""
BabelMeow Bridge — an Ollama-compatible HTTP server that answers translation
requests from RSTGameTranslation using our pre-translated cache.db.

Why Ollama-compatible: RSTGameTranslation can point its "Ollama" backend at any
URL. We pretend to be Ollama, but instead of running an LLM we:
    1. extract the source (EN) text from the request
    2. 3-layer match it against cache.db (exact / normalized / fuzzy)
    3. on miss (and if enabled) translate live via the REAL Ollama + cache it
    4. return the Thai text in Ollama's response shape

Ports:
    Bridge (this server):  11435   ← point RST here
    Real Ollama:           11434   ← used only for live fallback

Run:
    python -m babelmeow.overlay_bridge.server
    (or scripts/start_bridge.bat)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.overlay_bridge.matcher import Matcher
from babelmeow.runtime.cache import CacheEntry, TranslationCache
from babelmeow.translators import Glossary, OllamaTranslator, PostProcessor

# ───────── Config ─────────
DB_PATH = PROJECT_ROOT / "games" / "diablo4" / "cache.db"
GLOSSARY_PATH = PROJECT_ROOT / "games" / "diablo4" / "glossary.yaml"
REQUEST_LOG = PROJECT_ROOT / "bridge_requests.log"

BRIDGE_PORT = int(os.environ.get("BABELMEOW_PORT", "11435"))
# Real Ollama for live fallback. If the bridge itself runs on 11434 (because the
# real Ollama is stopped to free VRAM), live fallback must be off to avoid a self-loop.
REAL_OLLAMA = os.environ.get("BABELMEOW_REAL_OLLAMA", "http://localhost:11434")
MODEL_NAME = "babelmeow-th"          # the "model" RST will select
# Live fallback: translate cache-misses live via real Ollama. Disable while the
# batch is hogging Ollama (set BABELMEOW_LIVE=0). Default ON.
LIVE_FALLBACK = os.environ.get("BABELMEOW_LIVE", "1") != "0"
FUZZY_CUTOFF = 85.0

# Prompt wrappers RST/other tools may wrap around the source text.
# We strip these to recover the raw EN text. Extend after inspecting real traffic.
STRIP_PREFIXES = [
    "translate the following text to thai:",
    "translate to thai:",
    "translate this to thai:",
    "translate the following to thai:",
    "please translate to thai:",
]

# ───────── Globals (loaded at startup) ─────────
matcher: Matcher
cache: TranslationCache
translator: OllamaTranslator
processor: PostProcessor
live_system_prompt: str

app = FastAPI(title="BabelMeow Bridge")

_stats = {"exact": 0, "normalized": 0, "fuzzy": 0, "live": 0, "miss": 0, "requests": 0}

# Memoize per-segment results — RST re-sends the same UI labels/lines constantly,
# so the first lookup pays the cost and the rest are instant.
_memo: dict[str, str] = {}
_MEMO_MAX = 20000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_request(kind: str, raw: str, source: str, result) -> None:
    try:
        with open(REQUEST_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": _now_iso(),
                "endpoint": kind,
                "raw": raw[:300],
                "extracted": source[:200],
                "method": getattr(result, "method", "?"),
                "score": getattr(result, "score", 0),
                "th": (getattr(result, "th_text", None) or "")[:200],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


RST_SEPARATOR = "##|||##"


def parse_rst_payload(prompt: str) -> dict | None:
    """RST v5 embeds an input JSON after 'Here is the input JSON:'.
    Returns the parsed dict (with text_blocks) or None if not RST format."""
    marker = "input JSON:"
    idx = prompt.rfind(marker)
    if idx == -1:
        return None
    tail = prompt[idx + len(marker):]
    start = tail.find("{")
    end = tail.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(tail[start:end + 1])
    except Exception:
        return None


def handle_rst_blocks(payload: dict) -> str:
    """Translate each text_block, preserving IDs and ##|||## separators.
    Returns a JSON string of {"text_blocks":[{id,text}]} for RST."""
    out_blocks = []
    for b in payload.get("text_blocks", []):
        bid = b.get("id", "")
        raw_text = b.get("text", "") or ""
        segments = raw_text.split(RST_SEPARATOR)
        translated = []
        for seg in segments:
            s = seg.strip()
            if not s:
                translated.append(seg)  # keep empty/whitespace as-is
                continue
            th, _ = translate_text(s)
            translated.append(th)
        out_blocks.append({"id": bid, "text": RST_SEPARATOR.join(translated)})
    return json.dumps({"text_blocks": out_blocks}, ensure_ascii=False)


def extract_source_text(text: str) -> str:
    """Recover the raw EN text from a possibly-wrapped prompt."""
    if not text:
        return ""
    t = text.strip()
    low = t.lower()
    for pref in STRIP_PREFIXES:
        if low.startswith(pref):
            t = t[len(pref):].strip()
            low = t.lower()
    # Strip surrounding quotes the model/tool may add
    if len(t) >= 2 and t[0] in "\"'" and t[-1] in "\"'":
        t = t[1:-1].strip()
    return t


def translate_text(source: str) -> tuple[str, object]:
    """Return (thai_text, match_result). Falls back to live + cache on miss."""
    _stats["requests"] += 1

    # Memo hit — instant (RST repeats the same segments constantly)
    cached = _memo.get(source)
    if cached is not None:
        _stats["exact"] = _stats.get("exact", 0) + 1
        return cached, type("R", (), {"method": "memo", "score": 100, "th_text": cached})()

    result = matcher.lookup(source)

    if result.th_text is not None:
        _stats[result.method] = _stats.get(result.method, 0) + 1
        if len(_memo) < _MEMO_MAX:
            _memo[source] = result.th_text
        return result.th_text, result

    # MISS → live fallback
    if LIVE_FALLBACK and source.strip():
        try:
            tr = translator.translate(source, live_system_prompt)
            pp = processor.process(source, tr.th)
            cache.put(CacheEntry(
                en_text=source, th_text=pp.corrected, model=tr.model,
                category="live", needs_review=pp.needs_review,
                elapsed_ms=int(tr.elapsed_sec * 1000),
                warnings="; ".join(pp.warnings) if pp.warnings else None,
            ))
            matcher.add(source, pp.corrected)
            _stats["live"] += 1
            result.method = "live"
            result.th_text = pp.corrected
            return pp.corrected, result
        except Exception as e:
            sys.stderr.write(f"[live fallback error] {e}\n")

    _stats["miss"] += 1
    result.method = "miss"
    # Memoize misses too — otherwise every repeat re-runs the expensive
    # fuzzy+template search. (Static cache during play, so this is safe.)
    if len(_memo) < _MEMO_MAX:
        _memo[source] = source
    return source, result  # echo EN on total miss


# ───────── Ollama-compatible endpoints ─────────

@app.get("/")
def root():
    return {"status": "ok", "service": "BabelMeow Bridge", "cache_size": matcher.size}


@app.get("/api/version")
def version():
    return {"version": "0.1.0-babelmeow"}


@app.get("/api/tags")
def tags():
    """RST lists models here; advertise our pseudo-model."""
    return {
        "models": [{
            "name": f"{MODEL_NAME}:latest",
            "model": f"{MODEL_NAME}:latest",
            "modified_at": _now_iso(),
            "size": 0,
            "digest": "babelmeow",
            "details": {"family": "babelmeow", "parameter_size": "cache"},
        }]
    }


def _gen_response_obj(th: str) -> dict:
    return {
        "model": MODEL_NAME,
        "created_at": _now_iso(),
        "response": th,
        "done": True,
        "done_reason": "stop",
    }


@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    # DEBUG: dump the full request body so we can learn RST's exact prompt/JSON schema
    try:
        with open(PROJECT_ROOT / "bridge_lastreq.json", "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    raw = body.get("prompt", "") or ""
    stream = body.get("stream", False)

    # RST v5 format: prompt wraps an input JSON with text_blocks + ##|||## separators
    payload = parse_rst_payload(raw)
    if payload and "text_blocks" in payload:
        th = handle_rst_blocks(payload)   # th is a JSON string for RST to parse
        _log_request("generate-rst", raw, "[text_blocks]", type("R", (), {"method": "rst", "score": 0, "th_text": th})())
        if stream:
            def gen_rst():
                yield json.dumps(_gen_response_obj(th), ensure_ascii=False) + "\n"
            return StreamingResponse(gen_rst(), media_type="application/x-ndjson")
        return JSONResponse(_gen_response_obj(th))

    # Plain format (simple text in prompt)
    source = extract_source_text(raw)
    th, result = translate_text(source)
    _log_request("generate", raw, source, result)

    if stream:
        def gen():
            yield json.dumps(_gen_response_obj(th), ensure_ascii=False) + "\n"
        return StreamingResponse(gen(), media_type="application/x-ndjson")
    return JSONResponse(_gen_response_obj(th))


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", []) or []
    stream = body.get("stream", False)
    # Source = last user message content
    raw = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            raw = m.get("content", "") or ""
            break
    source = extract_source_text(raw)
    th, result = translate_text(source)
    _log_request("chat", raw, source, result)

    obj = {
        "model": MODEL_NAME,
        "created_at": _now_iso(),
        "message": {"role": "assistant", "content": th},
        "done": True,
        "done_reason": "stop",
    }
    if stream:
        def gen():
            yield json.dumps(obj, ensure_ascii=False) + "\n"
        return StreamingResponse(gen(), media_type="application/x-ndjson")
    return JSONResponse(obj)


@app.post("/v1/chat/completions")
async def openai_chat(request: Request):
    """OpenAI-compatible endpoint (some tools use this shape)."""
    body = await request.json()
    messages = body.get("messages", []) or []
    raw = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            raw = m.get("content", "") or ""
            break
    source = extract_source_text(raw)
    th, result = translate_text(source)
    _log_request("openai", raw, source, result)
    return JSONResponse({
        "id": "babelmeow-1",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_NAME,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": th},
            "finish_reason": "stop",
        }],
    })


@app.get("/stats")
def stats():
    total = max(_stats["requests"], 1)
    hit = _stats["exact"] + _stats["normalized"] + _stats["fuzzy"]
    return {
        **_stats,
        "cache_size": matcher.size,
        "hit_rate_pct": round(hit / total * 100, 1),
    }


@app.post("/reload")
def reload_cache():
    n = matcher.load()
    return {"reloaded": n}


def main():
    global matcher, cache, translator, processor, live_system_prompt
    print("=" * 60)
    print(" BabelMeow Bridge starting...")
    print("=" * 60)
    cache = TranslationCache(DB_PATH)
    glossary = Glossary.from_yaml(GLOSSARY_PATH)
    matcher = Matcher(DB_PATH, fuzzy_cutoff=FUZZY_CUTOFF)
    translator = OllamaTranslator(host=REAL_OLLAMA)
    processor = PostProcessor(glossary=glossary)
    live_system_prompt = translator.build_system(glossary.to_prompt_block())

    print(f"  Cache entries: {matcher.size:,}")
    print(f"  Glossary:      {len(glossary)} terms")
    print(f"  Live fallback: {'ON (via ' + REAL_OLLAMA + ')' if LIVE_FALLBACK else 'OFF'}")
    print(f"  Listening on:  http://localhost:{BRIDGE_PORT}")
    print(f"  → Point RSTGameTranslation's Ollama URL here, model '{MODEL_NAME}'")
    print("=" * 60)

    # Dual-stack socket: accept BOTH ::1 (localhost->IPv6) and 127.0.0.1 (IPv4).
    # Without this, clients resolving 'localhost' to ::1 hit a ~2s timeout before
    # falling back to IPv4 — making every new connection painfully slow.
    import socket
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # dual stack
        sock.bind(("::", BRIDGE_PORT))
        print("  Socket: dual-stack (IPv6 + IPv4) — localhost is fast")
        config = uvicorn.Config(app, log_level="warning")
        uvicorn.Server(config).run(sockets=[sock])
    except Exception as e:
        print(f"  Dual-stack failed ({e}); falling back to IPv4 only")
        uvicorn.run(app, host="127.0.0.1", port=BRIDGE_PORT, log_level="warning")


if __name__ == "__main__":
    main()
