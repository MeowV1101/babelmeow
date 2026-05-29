"""Tests for the translation post-processor."""

from __future__ import annotations

from babelmeow.translators.postprocess import PostProcessor


def test_glossary_auto_replace_leaked_english(glossary):
    pp = PostProcessor(glossary)
    # model left "Necromancer" untranslated in the output
    r = pp.process("The Necromancer", "เดอะ Necromancer")
    assert "เนโครแมนเซอร์" in r.corrected
    assert "Necromancer" not in r.corrected


def test_known_wrong_transliteration_fixed(glossary):
    pp = PostProcessor(glossary)
    r = pp.process("The Nephalem", "นีเฟลีมเป็นเผ่าพันธุ์")
    assert "เนฟาเลม" in r.corrected
    assert "นีเฟลีม" not in r.corrected


def test_placeholder_preserved_ok(glossary):
    pp = PostProcessor(glossary)
    r = pp.process("Go to {LEVELAREA}", "ไปที่ {LEVELAREA}")
    assert "{LEVELAREA}" in r.corrected
    assert not r.needs_review


def test_placeholder_restored_when_translated(glossary):
    pp = PostProcessor(glossary)
    # model "translated" the placeholder name
    r = pp.process("Go to {LEVELAREA}", "ไปที่ {พื้นที่}")
    assert "{LEVELAREA}" in r.corrected


def test_missing_placeholder_flags_review(glossary):
    pp = PostProcessor(glossary)
    # color tags dropped entirely, nothing to restore
    r = pp.process("{c_gold}Learn{/c}", "เรียนรู้")
    assert r.needs_review
    assert any("c_gold" in w for w in r.warnings)


def test_semantic_trap_fire_water(glossary):
    pp = PostProcessor(glossary)
    r = pp.process("a torrent of fire", "กระแสน้ำไฟ")
    assert r.needs_review
    assert any("fire/water" in w for w in r.warnings)


def test_clean_translation_no_review(glossary):
    pp = PostProcessor(glossary)
    r = pp.process("Hello world", "สวัสดีชาวโลก")
    assert not r.needs_review
    assert r.corrected == "สวัสดีชาวโลก"
