"""Tests for template index (dynamic-text matching)."""

from __future__ import annotations

from babelmeow.overlay_bridge.template import (
    TemplateIndex,
    has_content_placeholder,
)


def test_has_content_placeholder():
    assert has_content_placeholder("Slay {MONSTER}")
    assert has_content_placeholder("Depth {floor}")
    # markup-only is NOT a content placeholder
    assert not has_content_placeholder("{c_gold}hi{/c}")
    assert not has_content_placeholder("plain text")


def _index():
    idx = TemplateIndex()
    idx.build({
        "Slay {MONSTER}": "สังหาร {MONSTER}",
        "Pit Depth {floor}": "ความลึกหลุม {floor}",
        "Defeat the {MONSTER}: {LEFT}": "ปราบ {MONSTER}: {LEFT}",
        "{c_gold}hi{/c}": "สวัสดี",          # markup only -> not a template
        "{MONSTER}": "{MONSTER}",            # too generic -> excluded
        "plain": "ธรรมดา",                   # no placeholder -> excluded
    })
    return idx


def test_build_excludes_markup_and_generic():
    idx = _index()
    # only 3 real templates (Slay, Pit Depth, Defeat the)
    assert idx.count == 3


def test_match_single_text_placeholder():
    idx = _index()
    th, en = idx.match("Slay Lilith")
    assert en == "Slay {MONSTER}"
    assert th == "สังหาร Lilith"   # no translate_fn -> value kept verbatim


def test_match_with_translate_fn():
    idx = _index()
    th, _ = idx.match("Slay Lilith", translate_fn=lambda v: "ลิลิธ" if v == "Lilith" else None)
    assert th == "สังหาร ลิลิธ"


def test_match_numeric_kept():
    idx = _index()
    th, _ = idx.match("Pit Depth 99", translate_fn=lambda v: "SHOULD_NOT_RUN")
    assert th == "ความลึกหลุม 99"   # numeric value not translated


def test_match_two_placeholders():
    idx = _index()
    th, _ = idx.match("Defeat the Skeleton: 7")
    assert th == "ปราบ Skeleton: 7"


def test_no_match_returns_none():
    idx = _index()
    assert idx.match("Completely unrelated sentence") is None


def test_generic_template_does_not_match_everything():
    idx = _index()
    # "{MONSTER}" alone was excluded, so a random word must not match it
    assert idx.match("randomword") is None
