"""
Import a translation dictionary from a portable file into a cache.db.

The reverse of export_translations.py — lets you USE a dictionary someone else
made (JSON / CSV / PO / keyvalue) in the overlay. Auto-detects format by
extension (override with --format).

Usage:
  python scripts/import_dict.py --input shared_th.po --output mydict.db
  python scripts/import_dict.py --input export_th.csv -o cache.custom.db
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.runtime.cache import CacheEntry, TranslationCache

_PO_MSGID = re.compile(r'^msgid\s+"(.*)"\s*$')
_PO_MSGSTR = re.compile(r'^msgstr\s+"(.*)"\s*$')


def _po_unescape(s: str) -> str:
    return s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')


def parse_json(path: Path) -> list[tuple[str, str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("entries", [])
    out = []
    for it in items:
        src = it.get("source") or it.get("en_text") or it.get("en") or ""
        tgt = it.get("target") or it.get("th_text") or it.get("tgt") or ""
        if src and tgt:
            out.append((src, tgt, it.get("category", "imported")))
    return out


def parse_csv(path: Path) -> list[tuple[str, str, str]]:
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            src = r.get("source") or r.get("en_text") or ""
            tgt = r.get("target") or r.get("th_text") or ""
            if src and tgt:
                out.append((src, tgt, r.get("category", "imported")))
    return out


def parse_po(path: Path) -> list[tuple[str, str, str]]:
    out, msgid, msgstr, in_str = [], None, None, False
    for line in path.read_text(encoding="utf-8").splitlines():
        mi, ms = _PO_MSGID.match(line), _PO_MSGSTR.match(line)
        if mi:
            msgid, in_str = _po_unescape(mi.group(1)), False
        elif ms:
            msgstr, in_str = _po_unescape(ms.group(1)), True
        elif line.startswith('"') and line.endswith('"'):  # continuation
            frag = _po_unescape(line[1:-1])
            if in_str and msgstr is not None:
                msgstr += frag
            elif msgid is not None:
                msgid += frag
        elif not line.strip():
            if msgid and msgstr:
                out.append((msgid, msgstr, "imported"))
            msgid = msgstr = None
    if msgid and msgstr:
        out.append((msgid, msgstr, "imported"))
    return out


def parse_keyvalue(path: Path) -> list[tuple[str, str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if " = " in line:
            src, tgt = line.split(" = ", 1)
            if src and tgt:
                out.append((src, tgt, "imported"))
    return out


PARSERS = {"json": parse_json, "csv": parse_csv, "po": parse_po, "keyvalue": parse_keyvalue}
EXT_FMT = {".json": "json", ".csv": "csv", ".po": "po", ".txt": "keyvalue"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--format", choices=list(PARSERS), default=None)
    ap.add_argument("-o", "--output", required=True, help="cache .db to write/merge into")
    args = ap.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"[Error] not found: {inp}"); sys.exit(1)
    fmt = args.format or EXT_FMT.get(inp.suffix.lower())
    if not fmt:
        print(f"[Error] can't detect format from {inp.suffix}; pass --format"); sys.exit(1)

    rows = PARSERS[fmt](inp)
    if not rows:
        print("[Error] no source/target pairs found"); sys.exit(1)

    cache = TranslationCache(args.output)
    cache.put_many([CacheEntry(en_text=s, th_text=t, category=c, model="imported")
                    for s, t, c in rows])
    print(f"[Import] {fmt}: {len(rows):,} entries -> {args.output}")
    print(f"[Cache]  now {cache.stats()['total']:,} total")


if __name__ == "__main__":
    main()
