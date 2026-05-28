"""
Parse D4 translations exported from D4Analyzer.

Supports:
  - TSV from clipboard (Ctrl+A + Ctrl+C from D4Analyzer table)
  - JSON if D4Analyzer offers JSON export

Output: extracted/translations.json
  Schema: [{ sno, filename, index, key_hash, key, en_text, category }]

Usage:
    python scripts/parse_d4_strings.py extracted/translations.tsv
    python scripts/parse_d4_strings.py extracted/translations.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "games" / "diablo4" / "extracted"

# Categorize by filename pattern for smarter glossary application
CATEGORY_PATTERNS = [
    ("achievement", "achievement"),
    ("quest", "quest"),
    ("item", "item"),
    ("affix", "item_affix"),
    ("gem", "item"),
    ("rune", "item"),
    ("power", "skill"),
    ("ability", "skill"),
    ("class_", "class"),
    ("paladin", "class"),
    ("monster", "monster"),
    ("npc", "npc_dialog"),
    ("dialog", "npc_dialog"),
    ("quest_objective", "quest"),
    ("ui", "ui"),
    ("menu", "ui"),
    ("tutorial", "ui"),
    ("loadingscreen", "ui"),
    ("lore", "lore"),
    ("book", "lore"),
    ("journal", "lore"),
]


def categorize(filename: str) -> str:
    low = filename.lower()
    for pattern, category in CATEGORY_PATTERNS:
        if pattern in low:
            return category
    return "other"


def parse_tsv(path: Path) -> list[dict]:
    """Parse TSV exported from D4Analyzer clipboard."""
    rows: list[dict] = []
    with open(path, encoding="utf-8", newline="") as f:
        # First line may or may not be header — auto-detect
        reader = csv.reader(f, delimiter="\t")
        first = next(reader)

        # Check if first row looks like header
        header_keywords = {"SNO", "FileName", "Index", "KeyHash", "Key", "Translation"}
        is_header = any(h in header_keywords for h in first)

        if not is_header:
            # First row is data — process it
            rows.append(_row_to_dict(first))

        for row in reader:
            if len(row) < 6:
                continue  # skip malformed
            rows.append(_row_to_dict(row))

    return rows


def _row_to_dict(row: list[str]) -> dict:
    """Convert raw row to canonical dict."""
    sno, filename, index, key_hash, key, *rest = row
    en_text = "\t".join(rest).strip()
    return {
        "sno": sno.strip(),
        "filename": filename.strip(),
        "index": int(index) if index.strip().isdigit() else 0,
        "key_hash": key_hash.strip(),
        "key": key.strip(),
        "en_text": en_text,
        "category": categorize(filename),
    }


def parse_json(path: Path) -> list[dict]:
    """Parse JSON if D4Analyzer exports in JSON directly."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Try common shapes
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "entries" in data:
        items = data["entries"]
    elif isinstance(data, dict) and "translations" in data:
        items = data["translations"]
    else:
        # Treat dict as flat key→value
        items = [{"key": k, "en_text": v} for k, v in data.items()]

    # Normalize
    out = []
    for item in items:
        # Auto-pick fields by common names
        en_text = (
            item.get("Translation")
            or item.get("translation")
            or item.get("en_text")
            or item.get("text")
            or item.get("value")
            or ""
        )
        filename = (
            item.get("FileName")
            or item.get("filename")
            or item.get("file")
            or ""
        )
        out.append(
            {
                "sno": str(item.get("SNO") or item.get("sno") or ""),
                "filename": filename,
                "index": int(item.get("Index") or item.get("index") or 0),
                "key_hash": str(item.get("KeyHash") or item.get("key_hash") or ""),
                "key": item.get("Key") or item.get("key") or "",
                "en_text": en_text,
                "category": categorize(filename),
            }
        )
    return out


def summarize(rows: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    by_key: dict[str, int] = {}
    empty = 0
    total_chars = 0

    for r in rows:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
        by_key[r["key"]] = by_key.get(r["key"], 0) + 1
        if not r["en_text"]:
            empty += 1
        total_chars += len(r["en_text"])

    return {
        "total_entries": len(rows),
        "empty_entries": empty,
        "total_chars": total_chars,
        "avg_chars": round(total_chars / max(len(rows), 1), 1),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_key_top10": dict(
            sorted(by_key.items(), key=lambda x: -x[1])[:10]
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to TSV or JSON exported from D4Analyzer")
    ap.add_argument(
        "--output",
        default=str(OUT_DIR / "translations.json"),
        help="Output JSON path",
    )
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[Error] Input not found: {input_path}")
        sys.exit(1)

    print(f"[Parse] {input_path}")

    if input_path.suffix.lower() == ".json":
        rows = parse_json(input_path)
    else:
        rows = parse_tsv(input_path)

    print(f"[Loaded] {len(rows)} entries")

    summary = summarize(rows)
    print("\n[Summary]")
    print(f"  Total: {summary['total_entries']}")
    print(f"  Empty: {summary['empty_entries']}")
    print(f"  Total chars: {summary['total_chars']:,}")
    print(f"  Avg chars: {summary['avg_chars']}")
    print(f"\n  By category:")
    for cat, n in summary["by_category"].items():
        print(f"    {cat:20s} {n:>8,}")
    print(f"\n  Top key types:")
    for k, n in summary["by_key_top10"].items():
        print(f"    {k:30s} {n:>8,}")

    # Save normalized JSON
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "entries": rows},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n[Saved] {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
