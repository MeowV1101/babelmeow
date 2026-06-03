"""Round-trip tests: export writers -> import_dict parsers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from babelmeow.runtime.cache import TranslationCache

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import export_translations as ex  # noqa: E402
import import_dict as imp  # noqa: E402

_CFG = SimpleNamespace(game="test", target_lang="th")


def _roundtrip(cache_db, tmp_path, fmt, writer, parser, ext):
    rows = TranslationCache(cache_db).iter_all()
    f = tmp_path / f"d{ext}"
    writer(rows, f, _CFG)
    pairs = {s: t for s, t, _ in parser(f)}
    assert pairs.get("Lilith") == "ลิลิธ"
    assert pairs.get("Necromancer") == "เนโครแมนเซอร์"


def test_roundtrip_json(cache_db, tmp_path):
    _roundtrip(cache_db, tmp_path, "json", ex.write_json, imp.parse_json, ".json")


def test_roundtrip_csv(cache_db, tmp_path):
    _roundtrip(cache_db, tmp_path, "csv", ex.write_csv, imp.parse_csv, ".csv")


def test_roundtrip_po(cache_db, tmp_path):
    _roundtrip(cache_db, tmp_path, "po", ex.write_po, imp.parse_po, ".po")


def test_roundtrip_keyvalue(cache_db, tmp_path):
    _roundtrip(cache_db, tmp_path, "keyvalue", ex.write_keyvalue, imp.parse_keyvalue, ".txt")


def test_import_dict_writes_db(cache_db, tmp_path):
    rows = TranslationCache(cache_db).iter_all()
    f = tmp_path / "d.json"
    ex.write_json(rows, f, _CFG)
    pairs = imp.parse_json(f)
    out = tmp_path / "out.db"
    from babelmeow.runtime.cache import CacheEntry
    TranslationCache(out).put_many([CacheEntry(en_text=s, th_text=t, category=c) for s, t, c in pairs])
    assert TranslationCache(out).get("Lilith") == "ลิลิธ"
