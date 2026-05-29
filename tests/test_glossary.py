"""Tests for the glossary loader/lookup."""

from __future__ import annotations


def test_loads_all_sections(glossary):
    # characters + classes merged
    assert glossary["Lilith"] == "ลิลิธ"
    assert glossary["Necromancer"] == "เนโครแมนเซอร์"
    assert glossary["Rogue"] == "โร้ก"


def test_len(glossary):
    assert len(glossary) == 4  # Lilith, Nephalem, Necromancer, Rogue


def test_missing_key(glossary):
    assert glossary["Unknown"] is None


def test_find_en_in(glossary):
    found = dict(glossary.find_en_in("The Necromancer met Lilith"))
    assert found.get("Necromancer") == "เนโครแมนเซอร์"
    assert found.get("Lilith") == "ลิลิธ"
    assert "Rogue" not in found


def test_to_prompt_block(glossary):
    block = glossary.to_prompt_block()
    assert "Lilith = ลิลิธ" in block
    assert "Necromancer = เนโครแมนเซอร์" in block


def test_meta_excluded_from_terms(glossary):
    # _meta keys must not leak into terms
    assert "game" not in glossary.terms
    assert "source_lang" not in glossary.terms
