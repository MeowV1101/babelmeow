"""
Analyze extracted D4 strings: dedup, length distribution, top filenames,
and what's in the 'other' category.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT = PROJECT_ROOT / "games" / "diablo4" / "extracted" / "translations.json"


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    entries = data["entries"]
    print(f"[Loaded] {len(entries)} entries\n")

    # Dedup analysis
    unique_texts = set()
    text_counter: Counter[str] = Counter()
    for e in entries:
        t = e["en_text"]
        if t:
            unique_texts.add(t)
            text_counter[t] += 1

    print(f"[Dedup]")
    print(f"  Unique texts: {len(unique_texts):,}")
    print(f"  Duplicates saved: {len(entries) - len(unique_texts):,} "
          f"({(1 - len(unique_texts)/len(entries))*100:.1f}%)")

    print(f"\n[Top 20 duplicated strings]")
    for text, count in text_counter.most_common(20):
        preview = text[:60].replace("\n", " ")
        print(f"  {count:>5}× │ {preview}")

    # Length distribution
    lengths = [len(e["en_text"]) for e in entries if e["en_text"]]
    print(f"\n[Length distribution]")
    buckets = [(0, 5), (5, 20), (20, 50), (50, 100), (100, 300), (300, 999999)]
    for lo, hi in buckets:
        n = sum(1 for l in lengths if lo <= l < hi)
        bar = "█" * int(n / max(lengths) / 50 * 50) if lengths else ""
        print(f"  {lo:>3}-{hi:<6} chars: {n:>7,}")

    # What's in "other" category — look at filenames
    other_files: Counter[str] = Counter()
    for e in entries:
        if e["category"] == "other" and e["en_text"]:
            other_files[e["filename"]] += 1

    print(f"\n[Top 25 'other' category filenames]")
    for fn, n in other_files.most_common(25):
        print(f"  {n:>6,} │ {fn}")

    # Short strings (likely UI labels worth deduping)
    short_strings = [e for e in entries if 1 <= len(e["en_text"]) <= 10]
    short_unique = set(e["en_text"] for e in short_strings)
    print(f"\n[Short strings (1-10 chars)]")
    print(f"  Total: {len(short_strings):,}")
    print(f"  Unique: {len(short_unique):,}")
    print(f"  Sample: {sorted(list(short_unique))[:30]}")


if __name__ == "__main__":
    main()
