"""
Export a game's translation cache to a portable file.

Useful for: reusing translations elsewhere, hand-editing/reviewing, sharing,
or building a mod for a moddable game (Unity/Unreal — via that engine's tool).

Formats:
  json      : [{source, target, category, needs_review}]
  csv       : source,target,category,needs_review
  po        : gettext catalog (msgid=source, msgstr=target) — standard for
              app/game localization tools
  keyvalue  : "source = target" lines (simple, human-readable)

Usage:
  python scripts/export_translations.py --game diablo4 --lang th --format po
  python scripts/export_translations.py --game diablo4 --lang zh --format csv -o out.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.config import GameConfig
from babelmeow.runtime.cache import TranslationCache


def _po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def write_json(rows, out, cfg):
    data = [{"source": r["en_text"], "target": r["th_text"],
             "category": r["category"], "needs_review": bool(r["needs_review"])}
            for r in rows]
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(rows, out, cfg):
    with open(out, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig for Excel
        w = csv.writer(f)
        w.writerow(["source", "target", "category", "needs_review"])
        for r in rows:
            w.writerow([r["en_text"], r["th_text"], r["category"], int(r["needs_review"])])


def write_po(rows, out, cfg):
    lines = [
        'msgid ""', 'msgstr ""',
        f'"Project-Id-Version: BabelMeow {cfg.game}\\n"',
        f'"Language: {cfg.target_lang}\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        f'"X-Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}\\n"',
        "",
    ]
    for r in rows:
        if r["category"]:
            lines.append(f"#. category: {r['category']}")
        lines.append(f'msgid "{_po_escape(r["en_text"])}"')
        lines.append(f'msgstr "{_po_escape(r["th_text"])}"')
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def write_keyvalue(rows, out, cfg):
    lines = [f"{r['en_text']} = {r['th_text']}" for r in rows]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


WRITERS = {"json": write_json, "csv": write_csv, "po": write_po, "keyvalue": write_keyvalue}
EXT = {"json": ".json", "csv": ".csv", "po": ".po", "keyvalue": ".txt"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="diablo4")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--format", choices=list(WRITERS), default="json")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--exclude-review", action="store_true",
                    help="skip entries flagged needs_review")
    args = ap.parse_args()

    cfg = GameConfig.load(args.game, lang=args.lang)
    db = cfg.cache_db(cfg.target_lang)
    if not db.exists():
        print(f"[Error] cache not found: {db}"); sys.exit(1)

    rows = TranslationCache(db).iter_all()
    if args.exclude_review:
        rows = [r for r in rows if not r["needs_review"]]

    out = Path(args.output) if args.output else \
        cfg.root / f"export_{cfg.target_lang}{EXT[args.format]}"
    out.parent.mkdir(parents=True, exist_ok=True)
    WRITERS[args.format](rows, out, cfg)

    print(f"[Export] game={args.game} lang={cfg.target_lang} format={args.format}")
    print(f"[Wrote]  {len(rows):,} entries -> {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
