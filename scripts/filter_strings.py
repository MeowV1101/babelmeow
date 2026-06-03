"""
Filter D4 translations.json → MVP-ready unique input.

Filters applied (configurable):
- Drop Credits / FontIconTranslation / ButtonLegend / KeyNames files
- Drop empty strings
- Drop pure placeholders: (PH), (DNS), %d, %s, {key}-only, etc.
- Drop strings shorter than min_len (default 2 chars)
- Dedup by exact en_text match — keep first occurrence's metadata
- Optionally restrict to high-priority categories

Output: filtered_input.json with shape
    {
        "summary": {...},
        "entries": [
            { "en_text", "category", "filenames", "occurrences" },
            ...
        ]
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from babelmeow.config import GameConfig

# Patterns for strings that should NOT be translated
# (pure placeholders, format codes, identifiers)
SKIP_PATTERNS = [
    re.compile(r"^\(PH\)"),                         # placeholder marker
    re.compile(r"^\(DNS\)"),                        # do not ship
    re.compile(r"^%[dsifg]$"),                      # %d %s etc alone
    re.compile(r"^%\d+\$[a-z]$"),                   # %1$s alone
    re.compile(r"^\{[a-zA-Z0-9_]+\}$"),             # {Variable} alone
    re.compile(r"^\{[a-zA-Z0-9_]+\}\s*\{[a-zA-Z0-9_]+\}\s*$"),  # back to back
    re.compile(r"^[\s\d\.\,\-\:\;%]+$"),            # numbers/punctuation only
    re.compile(r"^[A-Z_]{2,}$"),                    # ALL_CAPS_TAGS only
    re.compile(r"^#\w*$"),                          # # tags
]


def should_skip(text: str, min_len: int) -> bool:
    if not text or not text.strip():
        return True
    if len(text) < min_len:
        return True
    for pat in SKIP_PATTERNS:
        if pat.match(text):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--input", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--min-len", type=int, default=2,
                    help="Min en_text length (default 2)")
    ap.add_argument("--categories", nargs="+", default=None,
                    help="Override priority categories (default: from game config)")
    args = ap.parse_args()

    cfg = GameConfig.load(args.game)
    in_path = Path(args.input) if args.input else cfg.translations_json
    out_path_arg = Path(args.output) if args.output else cfg.filtered_json
    DROPPED_FILES = cfg.dropped_files
    categories = set(args.categories) if args.categories else cfg.priority_categories

    data = json.loads(in_path.read_text(encoding="utf-8"))
    raw_entries = data["entries"]
    print(f"[Game] {args.game}  [Input] {in_path}")
    print(f"[Loaded] {len(raw_entries):,} raw entries")

    # Group by unique en_text
    seen: dict[str, dict] = {}
    occurrences: dict[str, int] = defaultdict(int)
    file_set: dict[str, set] = defaultdict(set)

    dropped_file = 0
    dropped_pattern = 0
    dropped_short = 0
    dropped_category = 0
    kept = 0

    for e in raw_entries:
        text = e["en_text"]
        fn = e["filename"]
        cat = e["category"]

        if fn in DROPPED_FILES:
            dropped_file += 1
            continue
        if not text or len(text) < args.min_len:
            dropped_short += 1
            continue
        if should_skip(text, args.min_len):
            dropped_pattern += 1
            continue
        if cat not in categories:
            dropped_category += 1
            continue

        occurrences[text] += 1
        file_set[text].add(fn)
        if text not in seen:
            seen[text] = {"category": cat, "first_file": fn, "key": e.get("key", "")}
            kept += 1

    print(f"\n[Filter results]")
    print(f"  Kept (unique):       {kept:,}")
    print(f"  Dropped (file):      {dropped_file:,}")
    print(f"  Dropped (pattern):   {dropped_pattern:,}")
    print(f"  Dropped (too short): {dropped_short:,}")
    print(f"  Dropped (category):  {dropped_category:,}")

    # Build output entries
    out_entries = []
    for text, meta in seen.items():
        out_entries.append({
            "en_text": text,
            "category": meta["category"],
            "first_file": meta["first_file"],
            "key": meta["key"],
            "occurrences": occurrences[text],
            "filenames": sorted(list(file_set[text]))[:5],  # cap to 5
        })

    # Sort by occurrences DESC (translate most-used first → cache hits matter)
    out_entries.sort(key=lambda x: -x["occurrences"])

    # Category breakdown
    by_cat: dict[str, int] = defaultdict(int)
    for e in out_entries:
        by_cat[e["category"]] += 1

    print(f"\n[By category (sorted)]")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} {n:>7,}")

    # Length stats
    lengths = [len(e["en_text"]) for e in out_entries]
    print(f"\n[Length stats]")
    print(f"  Min:  {min(lengths)}")
    print(f"  Max:  {max(lengths)}")
    print(f"  Mean: {sum(lengths)/len(lengths):.1f}")
    print(f"  Total chars: {sum(lengths):,}")

    summary = {
        "kept": kept,
        "dropped": {
            "file": dropped_file,
            "pattern": dropped_pattern,
            "short": dropped_short,
            "category": dropped_category,
        },
        "by_category": dict(sorted(by_cat.items(), key=lambda x: -x[1])),
        "total_chars": sum(lengths),
    }

    out_path = out_path_arg
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "entries": out_entries}, f, ensure_ascii=False, indent=2)

    print(f"\n[Saved] {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
