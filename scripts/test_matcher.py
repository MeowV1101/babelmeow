"""Test the 3-layer matcher against the live cache.db (read-only)."""

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

# Simulate OCR output: exact, case-changed, spaced, and OCR-error variants
TESTS = [
    ("Lilith", "exact-ish"),
    ("LILITH", "uppercase → normalized"),
    ("  Lilith  ", "padded → exact/normalized"),
    ("Necromancer", "exact-ish"),
    ("Necromaneer", "OCR error c→e → fuzzy"),
    ("Slay the Butcher", "phrase"),
    ("Slay the Buteher", "OCR error → fuzzy"),
    ("the pit", "lowercase → normalized"),
    ("Fractured Peaks", "location"),
    ("Fractured Peeks", "OCR error a→e → fuzzy"),
    ("Villager", "common word"),
    ("zzxqwv nonsense", "should miss"),
]


def main():
    t0 = time.time()
    m = Matcher(DB, fuzzy_cutoff=85.0)
    print(f"[Loaded] {m.size:,} cache entries in {time.time()-t0:.1f}s\n")
    print("=" * 78)

    timings = []
    for query, note in TESTS:
        t = time.time()
        r = m.lookup(query)
        elapsed_ms = (time.time() - t) * 1000
        timings.append(elapsed_ms)
        status = "✅" if r.th_text else "❌"
        print(f"{status} [{r.method:10s} {r.score:5.1f}] {elapsed_ms:5.1f}ms  ({note})")
        print(f"     IN : {query!r}")
        if r.th_text:
            print(f"     OUT: {r.th_text}  (matched: {r.matched_en!r})")
        print()

    print("=" * 78)
    print(f"Avg lookup: {sum(timings)/len(timings):.1f}ms | Max: {max(timings):.1f}ms")


if __name__ == "__main__":
    main()
