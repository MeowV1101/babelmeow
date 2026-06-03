"""
Batch translate D4 strings → SQLite cache.

Features:
- Parallel workers (configurable)
- Resume from cache (skip already-translated)
- Glossary enforcement via OllamaTranslator + PostProcessor
- Progress reporting with ETA
- Periodic checkpoint logging
- Graceful Ctrl-C handling

Usage:
    python scripts/translate_batch.py
    python scripts/translate_batch.py --limit 100  # smoke test
    python scripts/translate_batch.py --workers 4
    python scripts/translate_batch.py --model scb10x/typhoon-translate1.5-4b
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.config import GameConfig
from babelmeow.runtime.cache import CacheEntry, TranslationCache
from babelmeow.translators import Glossary, OllamaTranslator, PostProcessor

# Global stop flag for Ctrl-C
_STOP = threading.Event()


def _sigint(signum, frame):
    if _STOP.is_set():
        # Second Ctrl-C: force exit
        print("\n[Force exit]")
        sys.exit(130)
    print("\n[Signal] Stopping after current batch... (Ctrl-C again to force)")
    _STOP.set()


signal.signal(signal.SIGINT, _sigint)


class Stats:
    def __init__(self, total: int, start_skip: int):
        self.total = total
        self.start_skip = start_skip  # already-cached entries skipped at start
        self.done = 0
        self.errors = 0
        self.needs_review = 0
        self.lock = threading.Lock()
        self.t0 = time.time()

    def tick(self, *, error: bool = False, review: bool = False):
        with self.lock:
            self.done += 1
            if error:
                self.errors += 1
            if review:
                self.needs_review += 1

    def report(self) -> str:
        elapsed = time.time() - self.t0
        remaining = self.total - self.done
        rate = self.done / max(elapsed, 0.01)  # strings/sec
        eta_sec = remaining / max(rate, 0.001)
        eta_h = eta_sec / 3600
        return (
            f"[{self.done:>6,}/{self.total:,}] "
            f"err={self.errors} rev={self.needs_review} "
            f"rate={rate:.2f}/s elapsed={elapsed/60:.1f}min eta={eta_h:.1f}h"
        )


def translate_one(
    entry: dict,
    translator: OllamaTranslator,
    processor: PostProcessor,
    cache: TranslationCache,
    system: str,
    stats: Stats,
):
    if _STOP.is_set():
        return
    en = entry["en_text"]
    category = entry.get("category", "other")
    try:
        result = translator.translate(en, system)
        pp = processor.process(en, result.th)
        cache.put(
            CacheEntry(
                en_text=en,
                th_text=pp.corrected,
                model=result.model,
                category=category,
                needs_review=pp.needs_review,
                elapsed_ms=int(result.elapsed_sec * 1000),
                warnings="; ".join(pp.warnings) if pp.warnings else None,
            )
        )
        stats.tick(review=pp.needs_review)
    except Exception as e:
        stats.tick(error=True)
        sys.stderr.write(f"\n[Error] {en[:60]}... : {e}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--lang", default=None, help="target language (default: game config)")
    ap.add_argument("--input", default=None)
    ap.add_argument("--db", default=None)
    ap.add_argument("--glossary", default=None)
    ap.add_argument("--model", default=None, help="Ollama model (default: game config)")
    ap.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    ap.add_argument("--workers", type=int, default=4, help="Parallel workers")
    ap.add_argument("--limit", type=int, default=None, help="Only translate N strings (smoke test)")
    ap.add_argument("--report-every", type=int, default=10, help="Print progress every N")
    args = ap.parse_args()

    cfg = GameConfig.load(args.game, lang=args.lang)
    in_path = Path(args.input) if args.input else cfg.filtered_json
    db_path = Path(args.db) if args.db else cfg.cache_db(cfg.target_lang)
    glossary_path = Path(args.glossary) if args.glossary else cfg.glossary_path(cfg.target_lang)
    model = args.model or cfg.model_batch

    # Load
    cache = TranslationCache(db_path)
    glossary = Glossary.from_yaml(glossary_path)
    translator = OllamaTranslator(model=model, host=args.host, target_lang=cfg.target_lang,
                                  source_lang=cfg.source_lang)
    processor = PostProcessor(glossary=glossary, lang=cfg.target_lang)
    system = translator.build_system(glossary.to_prompt_block())

    print(f"[Config]")
    print(f"  Game:     {args.game}  ({cfg.source_lang} -> {cfg.target_lang})")
    print(f"  Model:    {model}")
    print(f"  Workers:  {args.workers}")
    print(f"  DB:       {db_path}")
    print(f"  Glossary: {len(glossary)} terms")
    print(f"  Input:    {in_path}")

    data = json.loads(in_path.read_text(encoding="utf-8"))
    all_entries = data["entries"]
    if args.limit:
        all_entries = all_entries[: args.limit]

    # Resume: skip entries already in cache
    existing = cache.existing_en_texts()
    pending = [e for e in all_entries if e["en_text"] not in existing]
    skipped = len(all_entries) - len(pending)
    print(f"  Total:    {len(all_entries):,}")
    print(f"  Cached:   {skipped:,} (resume — skipped)")
    print(f"  Pending:  {len(pending):,}\n")

    if not pending:
        print("[Done] Nothing to translate.")
        print(json.dumps(cache.stats(), indent=2, ensure_ascii=False))
        return

    stats = Stats(total=len(pending), start_skip=skipped)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                translate_one, e, translator, processor, cache, system, stats
            )
            for e in pending
        ]
        last_report = 0
        for fut in as_completed(futures):
            if stats.done - last_report >= args.report_every:
                print(stats.report(), flush=True)
                last_report = stats.done
            if _STOP.is_set():
                # Cancel remaining
                for f in futures:
                    f.cancel()
                break

    elapsed = time.time() - start_time
    print(f"\n[Done] {stats.done:,} translated, "
          f"{stats.errors} errors, {stats.needs_review} need review")
    print(f"Total time: {elapsed/60:.1f} min")
    if stats.done > 0:
        print(f"Avg: {elapsed/stats.done:.2f}s/string")
    print(f"\n[Cache stats]")
    print(json.dumps(cache.stats(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
