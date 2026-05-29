"""Tests for the 3+1 layer matcher (exact/normalized/template/fuzzy)."""

from __future__ import annotations

import pytest

from babelmeow.overlay_bridge.matcher import Matcher, normalize


@pytest.fixture
def matcher(cache_db):
    return Matcher(cache_db)


# ───────── normalize() ─────────

def test_normalize_lowercase_and_ws():
    assert normalize("  Hello   World  ") == "hello world"


def test_normalize_strips_markup_and_punct():
    assert normalize("{c_gold}Right-click!{/c}") == "right click"


# ───────── exact ─────────

def test_exact(matcher):
    r = matcher.lookup("Lilith")
    assert r.method == "exact"
    assert r.th_text == "ลิลิธ"


def test_exact_trimmed(matcher):
    r = matcher.lookup("  Lilith  ")
    assert r.th_text == "ลิลิธ"


# ───────── normalized ─────────

def test_normalized_uppercase(matcher):
    r = matcher.lookup("NECROMANCER")
    assert r.method == "normalized"
    assert r.th_text == "เนโครแมนเซอร์"


def test_markup_only_via_normalized(matcher):
    # "{c_gold}Right-click{/c}" stored; OCR sees "Right-click"
    r = matcher.lookup("Right-click")
    assert r.th_text == "คลิกขวา"


# ───────── fuzzy ─────────

def test_fuzzy_ocr_error(matcher):
    r = matcher.lookup("Necromaneer")  # c -> e
    assert r.method == "fuzzy"
    assert r.th_text == "เนโครแมนเซอร์"


def test_fuzzy_length_guard_rejects_substring(matcher):
    # long nonsense must not match a short cache key
    r = matcher.lookup("zzxqwv totally unrelated nonsense")
    assert r.method == "miss"
    assert r.th_text is None


# ───────── template ─────────

def test_template_text_value_retranslated(matcher):
    r = matcher.lookup("Slay Butcher")
    assert r.method == "template"
    assert r.th_text == "สังหาร บุชเชอร์"   # Butcher -> บุชเชอร์


def test_template_numeric_value_kept(matcher):
    r = matcher.lookup("Pit Depth 45")
    assert r.method == "template"
    assert r.th_text == "ความลึกหลุม 45"


def test_template_two_placeholders(matcher):
    r = matcher.lookup("Defeat the Butcher: 3")
    assert r.method == "template"
    assert r.th_text == "ปราบ บุชเชอร์: 3"


def test_template_runs_before_fuzzy(matcher):
    # "Slay Butcher" should template-match, not fuzzy-match "Butcher"
    r = matcher.lookup("Slay Butcher")
    assert r.method == "template"


# ───────── miss ─────────

def test_total_miss(matcher):
    r = matcher.lookup("qwertyuiop asdfghjkl")
    assert r.method == "miss"


def test_empty_input(matcher):
    r = matcher.lookup("")
    assert r.method == "miss"


# ───────── add() ─────────

def test_add_updates_index(matcher):
    matcher.add("Brand New", "ของใหม่")
    r = matcher.lookup("Brand New")
    assert r.th_text == "ของใหม่"
