"""
Offline quality pass: re-translate live-discovered entries with the high-quality
8B model + full glossary, replacing the fast 4B live translations.

Workflow:
  1. Play with live fallback ON -> 4B translates cache-misses on the fly (category='live')
  2. Between sessions (game closed), run this -> 8B re-translates them with glossary
  3. Entries marked category='live_8b', verified=1 -> high quality, permanent
  4. Eventually live fallback rarely fires -> can disable it (VRAM 0 at runtime)

Usage:
    python scripts/upgrade_live.py                       # upgrade all category='live'
    python scripts/upgrade_live.py --host http://127.0.0.1:11435
    python scripts/upgrade_live.py --model scb10x/llama3.1-typhoon2-8b-instruct
    python scripts/upgrade_live.py --limit 20            # test on a few
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.config import GameConfig
from babelmeow.translators import Glossary, OllamaTranslator, PostProcessor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--db", default=None)
    ap.add_argument("--host", default="http://127.0.0.1:11435")
    ap.add_argument("--model", default=None)
    ap.add_argument("--category", default="live", help="category to upgrade")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cfg = GameConfig.load(args.game, lang=args.lang)
    db_path = args.db or str(cfg.cache_db(cfg.target_lang))
    glossary = Glossary.from_yaml(cfg.glossary_path(cfg.target_lang))
    translator = OllamaTranslator(model=args.model or cfg.model_batch, host=args.host,
                                  target_lang=cfg.target_lang)
    processor = PostProcessor(glossary=glossary, lang=cfg.target_lang)
    system = translator.build_system(glossary.to_prompt_block())  # full glossary prompt

    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT en_text FROM translations WHERE category=?",
        (args.category,),
    ).fetchall()
    targets = [r["en_text"] for r in rows]
    if args.limit:
        targets = targets[: args.limit]

    print(f"[Upgrade] {len(targets)} '{args.category}' entries via {translator.model}")
    if not targets:
        print("Nothing to upgrade.")
        return

    t0 = time.time()
    done = 0
    for en in targets:
        try:
            tr = translator.translate(en, system)
            pp = processor.process(en, tr.th)
            conn.execute(
                "UPDATE translations SET th_text=?, model=?, category='live_8b', "
                "verified=1, needs_review=?, updated_at=datetime('now') WHERE en_text=?",
                (pp.corrected, tr.model, int(pp.needs_review), en),
            )
            conn.commit()
            done += 1
            if done % 10 == 0:
                rate = done / (time.time() - t0)
                print(f"  {done}/{len(targets)} ({rate:.2f}/s)")
        except Exception as e:
            sys.stderr.write(f"[err] {en[:50]}: {e}\n")

    conn.close()
    elapsed = time.time() - t0
    print(f"\n[Done] upgraded {done}/{len(targets)} in {elapsed/60:.1f} min")
    print("Reload bridge (/reload) to serve upgraded translations.")


if __name__ == "__main__":
    main()
