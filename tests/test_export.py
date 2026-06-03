"""Tests for export writers."""

from __future__ import annotations

import csv
import json
import sys
from types import SimpleNamespace

from babelmeow.runtime.cache import TranslationCache

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"))
import export_translations as ex  # noqa: E402

_CFG = SimpleNamespace(game="test", target_lang="th")


def _rows(cache_db):
    return TranslationCache(cache_db).iter_all()


def test_iter_all_returns_rows(cache_db):
    rows = _rows(cache_db)
    assert len(rows) >= 10
    assert {"en_text", "th_text", "category"} <= set(rows[0])


def test_export_json(cache_db, tmp_path):
    out = tmp_path / "o.json"
    ex.write_json(_rows(cache_db), out, _CFG)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert any(d["source"] == "Lilith" and d["target"] == "ลิลิธ" for d in data)


def test_export_csv(cache_db, tmp_path):
    out = tmp_path / "o.csv"
    ex.write_csv(_rows(cache_db), out, _CFG)
    with open(out, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0].keys() >= {"source", "target", "category", "needs_review"}
    assert any(r["target"] == "ลิลิธ" for r in rows)


def test_export_po(cache_db, tmp_path):
    out = tmp_path / "o.po"
    ex.write_po(_rows(cache_db), out, _CFG)
    text = out.read_text(encoding="utf-8")
    assert 'msgid ""' in text                      # header
    assert "Language: th" in text
    assert 'msgid "Lilith"' in text
    assert 'msgstr "ลิลิธ"' in text


def test_export_po_escaping(cache_db, tmp_path):
    # ensure quotes/newlines in content are escaped
    assert ex._po_escape('a"b\nc') == 'a\\"b\\nc'


def test_export_keyvalue(cache_db, tmp_path):
    out = tmp_path / "o.txt"
    ex.write_keyvalue(_rows(cache_db), out, _CFG)
    text = out.read_text(encoding="utf-8")
    assert "Lilith = ลิลิธ" in text
