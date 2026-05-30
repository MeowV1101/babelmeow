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

from babelmeow.translators import Glossary, OllamaTranslator, PostProcessor

DB = PROJECT_ROOT / "games" / "diablo4" / "cache.db"
GLOSSARY = PROJECT_ROOT / "games" / "diablo4" / "glossary.yaml"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--host", default="http://127.0.0.1:11435")
    ap.add_argument("--model", default="scb10x/llama3.1-typhoon2-8b-instruct")
    ap.add_argument("--category", default="live", help="category to upgrade")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    glossary = Glossary.from_yaml(GLOSSARY)
    translator = OllamaTranslator(model=args.model, host=args.host)
    processor = PostProcessor(glossary=glossary)
    system = translator.build_system(glossary.to_prompt_block())  # full glossary prompt

    conn = sqlite3.connect(args.db, timeout=30.0)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT en_text FROM translations WHERE category=?",
        (args.category,),
    ).fetchall()
    targets = [r["en_text"] for r in rows]
    if args.limit:
        targets = targets[: args.limit]

    print(f"[Upgrade] {len(targets)} '{args.category}' entries via {args.model}")
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
