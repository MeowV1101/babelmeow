"""Shared pytest fixtures: a small deterministic cache + glossary."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from babelmeow.runtime.cache import CacheEntry, TranslationCache
from babelmeow.translators.glossary import Glossary

# Known EN -> TH pairs covering every matcher layer.
SAMPLE_TRANSLATIONS = {
    # plain
    "Lilith": "ลิลิธ",
    "Necromancer": "เนโครแมนเซอร์",
    "Fractured Peaks": "ยอดเขาร้าวราน",
    "The Pit": "แอ่งนรก",
    "Butcher": "บุชเชอร์",
    "Villager": "ชาวบ้าน",
    # markup-only placeholder -> resolved via normalized layer
    "{c_gold}Right-click{/c}": "คลิกขวา",
    # content-placeholder templates
    "Slay {MONSTER}": "สังหาร {MONSTER}",
    "Pit Depth {floor}": "ความลึกหลุม {floor}",
    "Defeat the {MONSTER}: {LEFT}": "ปราบ {MONSTER}: {LEFT}",
}

GLOSSARY_YAML = """\
_meta:
  game: Test
  source_lang: en
  target_lang: th
characters:
  Lilith: ลิลิธ
  Nephalem: เนฟาเลม
classes:
  Necromancer: เนโครแมนเซอร์
  Rogue: โร้ก
"""


@pytest.fixture
def cache_db(tmp_path) -> Path:
    """Create a temp SQLite cache populated with SAMPLE_TRANSLATIONS."""
    db = tmp_path / "cache.db"
    cache = TranslationCache(db)
    cache.put_many([
        CacheEntry(en_text=en, th_text=th, category="test")
        for en, th in SAMPLE_TRANSLATIONS.items()
    ])
    return db


@pytest.fixture
def cache(cache_db) -> TranslationCache:
    return TranslationCache(cache_db)


@pytest.fixture
def glossary(tmp_path) -> Glossary:
    p = tmp_path / "glossary.yaml"
    p.write_text(GLOSSARY_YAML, encoding="utf-8")
    return Glossary.from_yaml(p)
