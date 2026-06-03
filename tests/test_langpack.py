"""Tests for language packs + language-parameterized translator/postprocess."""

from __future__ import annotations

from babelmeow.langpack import LangPack
from babelmeow.translators.ollama import OllamaTranslator
from babelmeow.translators.postprocess import PostProcessor


# ───────── LangPack loading ─────────

def test_load_thai():
    lp = LangPack.load("th")
    assert lp.name == "Thai"
    assert lp.prompt_style                      # non-empty style
    assert lp.few_shot                          # has examples
    assert lp.wrong_transliterations            # has fix rules
    assert lp.semantic_traps


def test_load_chinese():
    lp = LangPack.load("zh")
    assert lp.name == "Chinese"
    assert lp.few_shot
    assert any("屠夫" in ex.get("tgt", "") for ex in lp.few_shot)


def test_load_unknown_lang_safe_defaults():
    lp = LangPack.load("xx")
    assert lp.name == "xx"
    assert lp.few_shot == []
    assert lp.wrong_transliterations == {}


def test_few_shot_block_format():
    lp = LangPack.load("th")
    block = lp.few_shot_block("EN")
    assert "EN:" in block and "TGT:" in block


# ───────── prompt parameterization ─────────

def test_prompt_thai():
    s = OllamaTranslator(target_lang="th").build_system("- Lilith = ลิลิธ")
    assert "English to Thai" in s
    assert "บุชเชอร์" in s          # Thai few-shot injected


def test_prompt_chinese():
    s = OllamaTranslator(target_lang="zh").build_system("- Lilith = 莉莉丝")
    assert "English to Chinese" in s
    assert "屠夫" in s              # Chinese few-shot injected
    assert "บุชเชอร์" not in s       # no Thai leak


def test_translator_target_name_from_langpack():
    assert OllamaTranslator(target_lang="zh").target_lang_name == "Chinese"
    assert OllamaTranslator(target_lang="th").target_lang_name == "Thai"


# ───────── postprocess uses langpack rules ─────────

def test_postprocess_th_rules_from_langpack(glossary):
    pp = PostProcessor(glossary, lang="th")
    # Thai wrong-transliteration rule still applies
    r = pp.process("The Nephalem", "นีเฟลีมเป็นเผ่าพันธุ์")
    assert "เนฟาเลม" in r.corrected


def test_postprocess_zh_loads_zh_rules(glossary):
    pp = PostProcessor(glossary, lang="zh")
    # zh langpack has a fire/water-or-ice trap
    assert any("fire" in t[2] for t in pp.traps)
    # Thai-only transliteration rules must NOT be applied for zh
    assert "นีเฟลีมี" not in pp.wrong
