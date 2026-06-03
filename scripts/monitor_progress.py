"""
Monitor batch translation progress.

Quick stats from cache.db + ETA estimate.
Run anytime: python scripts/monitor_progress.py
"""

from __future__ import annotations

import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from babelmeow.config import GameConfig

TOTAL_TARGET = 96061  # from filter_strings.py output


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--lang", default=None)
    args = ap.parse_args()
    cfg = GameConfig.load(args.game, lang=args.lang)
    DB = cfg.cache_db(cfg.target_lang)
    if not DB.exists():
        print(f"[Error] Cache DB not found at {DB}")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) AS n FROM translations").fetchone()["n"]
    review = conn.execute(
        "SELECT COUNT(*) AS n FROM translations WHERE needs_review=1"
    ).fetchone()["n"]
    avg_ms = conn.execute(
        "SELECT AVG(elapsed_ms) AS avg FROM translations WHERE elapsed_ms IS NOT NULL"
    ).fetchone()["avg"] or 0

    # Recent rate (last 5 min)
    # NOTE: updated_at is ISO format "2026-05-29T08:20:54+00:00" (T separator + TZ).
    # SQLite datetime('now') uses a space separator, so a raw string compare breaks.
    # Normalize with datetime(replace(...,'T',' ')) for a correct UTC comparison.
    recent = conn.execute(
        "SELECT COUNT(*) AS n FROM translations "
        "WHERE datetime(replace(substr(updated_at,1,19),'T',' ')) "
        "> datetime('now', '-5 minutes')"
    ).fetchone()["n"]

    # Per-category
    by_cat = conn.execute(
        "SELECT category, COUNT(*) AS n FROM translations GROUP BY category ORDER BY n DESC"
    ).fetchall()

    # First/last timestamps for total elapsed
    times = conn.execute(
        "SELECT MIN(created_at) AS first, MAX(updated_at) AS last FROM translations"
    ).fetchone()

    progress = total / TOTAL_TARGET * 100
    remaining = TOTAL_TARGET - total

    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  BabelMeow — Translation Progress Monitor                  ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    print(f"║  Done:        {total:>7,} / {TOTAL_TARGET:,}  ({progress:.1f}%)            ║")
    print(f"║  Remaining:   {remaining:>7,}                                 ║")
    print(f"║  Needs review:{review:>7,}                                 ║")
    print(f"║  Recent (5m): {recent:>7,}                                 ║")
    print(f"║  Avg elapsed: {avg_ms/1000:>6.1f}s per string                       ║")

    if recent > 0:
        rate_per_sec = recent / 300  # 5 min = 300 sec
        eta_sec = remaining / max(rate_per_sec, 0.001)
        eta_h = eta_sec / 3600
        print(f"║  Current rate:{rate_per_sec:>6.2f}/s  (5-worker GPU target ~2.0/s)   ║")
        print(f"║  ETA:         {eta_h:>6.1f} hours ({eta_h/24:.1f} days)              ║")
    else:
        print(f"║  Rate:        not active (no entries in last 5 min)        ║")

    print(f"╚════════════════════════════════════════════════════════════╝")

    print(f"\n[By category]")
    for r in by_cat:
        bar_len = int(r["n"] / max(total, 1) * 40)
        bar = "█" * bar_len
        print(f"  {(r['category'] or 'none'):15s} {r['n']:>7,} {bar}")

    if times["first"]:
        print(f"\n[Timing]")
        print(f"  First entry: {times['first']}")
        print(f"  Last entry:  {times['last']}")

    # Sample most recent translations
    print(f"\n[Latest 5 translations]")
    recent_rows = conn.execute(
        "SELECT en_text, th_text, category, needs_review FROM translations "
        "ORDER BY updated_at DESC LIMIT 5"
    ).fetchall()
    for r in recent_rows:
        flag = " ⚠️" if r["needs_review"] else ""
        print(f"  [{r['category']}]{flag}")
        print(f"    EN: {r['en_text'][:70]}")
        print(f"    TH: {r['th_text'][:70]}")


if __name__ == "__main__":
    main()
