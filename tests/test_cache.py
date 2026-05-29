"""Tests for the SQLite translation cache."""

from __future__ import annotations

from babelmeow.runtime.cache import CacheEntry, TranslationCache


def test_get_exact(cache):
    assert cache.get("Lilith") == "ลิลิธ"


def test_get_missing_returns_none(cache):
    assert cache.get("does not exist") is None


def test_has(cache):
    assert cache.has("Necromancer")
    assert not cache.has("nope")


def test_get_many(cache):
    res = cache.get_many(["Lilith", "Butcher", "missing"])
    assert res == {"Lilith": "ลิลิธ", "Butcher": "บุชเชอร์"}


def test_get_many_empty(cache):
    assert cache.get_many([]) == {}


def test_put_then_get(cache):
    cache.put(CacheEntry(en_text="New Term", th_text="คำใหม่", category="test"))
    assert cache.get("New Term") == "คำใหม่"


def test_put_upsert_updates(cache):
    cache.put(CacheEntry(en_text="Lilith", th_text="ลิลิธแก้ไข", category="test"))
    assert cache.get("Lilith") == "ลิลิธแก้ไข"


def test_existing_en_texts_for_resume(cache):
    existing = cache.existing_en_texts()
    assert "Lilith" in existing
    assert "Butcher" in existing


def test_stats(cache):
    s = cache.stats()
    assert s["total"] >= 10
    assert "by_category" in s


def test_needs_review_flag(tmp_path):
    db = tmp_path / "c.db"
    c = TranslationCache(db)
    c.put(CacheEntry(en_text="X", th_text="ก", needs_review=True, category="t"))
    c.put(CacheEntry(en_text="Y", th_text="ข", needs_review=False, category="t"))
    assert c.stats()["needs_review"] == 1
