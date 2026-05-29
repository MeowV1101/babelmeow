"""Test template (dynamic-text) matching against live cache.db."""

from __future__ import annotations

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.overlay_bridge.matcher import Matcher

DB = PROJECT_ROOT / "games" / "diablo4" / "cache.db"

# Simulated OCR of rendered (placeholder-substituted) in-game text
TESTS = [
    "Defeat the Butcher",          # {MONSTER} -> Butcher (re-translate)
    "Slay Lilith",                 # {MONSTER} -> Lilith
    "Pit Depth 45",                # {floor} -> 45 (number, keep)
    "Travel to the Fractured Peaks",  # {LEVELAREA} -> known location
    "Free the Prisoners: 3",       # {LEFT} -> 3
    "Destroy the Skeleton: 5",     # 2 placeholders
]


def main():
    t0 = time.time()
    m = Matcher(DB)
    print(f"[Loaded] {m.size:,} entries, {m.template_count:,} templates "
          f"in {time.time()-t0:.1f}s\n")
    print("=" * 78)

    timings = []
    for q in TESTS:
        t = time.time()
        r = m.lookup(q)
        ms = (time.time() - t) * 1000
        timings.append(ms)
        status = "✅" if r.th_text else "❌"
        print(f"{status} [{r.method:10s}] {ms:5.1f}ms")
        print(f"     IN : {q}")
        if r.th_text:
            print(f"     OUT: {r.th_text}")
            print(f"     via: {r.matched_en!r}")
        print()

    print("=" * 78)
    print(f"Avg: {sum(timings)/len(timings):.1f}ms | Max: {max(timings):.1f}ms")


if __name__ == "__main__":
    main()
