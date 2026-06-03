"""
Generic string importer — turn a game's extracted strings into translations.json.

The engine-specific EXTRACTION is done by external tools (D4Analyzer for CASC,
AssetStudio for Unity, FModel for Unreal, ...). This script only IMPORTS the
result into BabelMeow's normalized format, driven by the game's config.yaml.

Formats (config: importer.format):
  d4analyzer : D4Analyzer "Copy Selected" TSV
               (SNO, FileName, Index, KeyHash, Key, Translation)
  tsv / csv  : delimited file; map columns via importer.columns
               (source [required], filename, key, key_hash)
  json       : list of objects; map keys via importer.columns

Usage:
  python scripts/import_strings.py --game diablo4 --input path/to/export.tsv
  python scripts/import_strings.py --game mygame --input strings.csv
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
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.config import GameConfig

_D4_HEADER = {"SNO", "FileName", "Index", "KeyHash", "Key", "Translation"}


def _entry(cfg: GameConfig, source, filename="", key="", key_hash="", index=0):
    return {
        "sno": "",
        "filename": filename or "",
        "index": int(index) if str(index).isdigit() else 0,
        "key_hash": str(key_hash or ""),
        "key": key or "",
        "en_text": (source or "").strip(),
        "category": cfg.categorize(filename or ""),
    }


def parse_d4analyzer(path: Path, cfg: GameConfig) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        first = next(reader, None)
        if first and not any(h in _D4_HEADER for h in first):
            if len(first) >= 6:  # first line was data, not header
                rows.append(_entry(cfg, "\t".join(first[5:]), first[1], first[4], first[3], first[2]))
        for row in reader:
            if len(row) < 6:
                continue
            rows.append(_entry(cfg, "\t".join(row[5:]), row[1], row[4], row[3], row[2]))
    return rows


def parse_delimited(path: Path, cfg: GameConfig, delim: str) -> list[dict]:
    cols = cfg.importer.get("columns", {})
    src_c = cols.get("source", "source")
    fn_c, key_c, kh_c = cols.get("filename"), cols.get("key"), cols.get("key_hash")
    rows: list[dict] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        for r in reader:
            src = r.get(src_c, "")
            if not src:
                continue
            rows.append(_entry(cfg, src, r.get(fn_c, "") if fn_c else "",
                               r.get(key_c, "") if key_c else "",
                               r.get(kh_c, "") if kh_c else ""))
    return rows


def parse_json(path: Path, cfg: GameConfig) -> list[dict]:
    cols = cfg.importer.get("columns", {})
    src_c = cols.get("source", "source")
    fn_c, key_c, kh_c = cols.get("filename"), cols.get("key"), cols.get("key_hash")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("entries", [])
    rows: list[dict] = []
    for it in items:
        if isinstance(it, dict):
            src = it.get(src_c) or it.get("source") or it.get("en_text") or ""
            rows.append(_entry(cfg, src, it.get(fn_c, "") if fn_c else "",
                               it.get(key_c, "") if key_c else "",
                               it.get(kh_c, "") if kh_c else ""))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--input", required=True, help="raw export file from the engine tool")
    ap.add_argument("--format", default=None, help="override importer.format (d4analyzer/tsv/csv/json)")
    ap.add_argument("--output", default=None, help="override output translations.json")
    args = ap.parse_args()

    cfg = GameConfig.load(args.game)
    fmt = args.format or cfg.importer.get("format", "tsv")
    inp = Path(args.input)
    if not inp.exists():
        print(f"[Error] input not found: {inp}"); sys.exit(1)

    print(f"[Import] game={args.game} format={fmt} input={inp.name}")
    if fmt == "d4analyzer":
        rows = parse_d4analyzer(inp, cfg)
    elif fmt == "tsv":
        rows = parse_delimited(inp, cfg, "\t")
    elif fmt == "csv":
        rows = parse_delimited(inp, cfg, ",")
    elif fmt == "json":
        rows = parse_json(inp, cfg)
    else:
        print(f"[Error] unknown format: {fmt}"); sys.exit(1)

    # category summary
    by_cat: dict[str, int] = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1

    out = Path(args.output) if args.output else cfg.translations_json
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = {"total_entries": len(rows), "by_category": dict(sorted(by_cat.items(), key=lambda x: -x[1]))}
    out.write_text(json.dumps({"summary": summary, "entries": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[Loaded] {len(rows):,} entries")
    for cat, n in summary["by_category"].items():
        print(f"  {cat:14s} {n:>7,}")
    print(f"[Saved] {out}")


if __name__ == "__main__":
    main()
