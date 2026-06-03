"""
Per-game configuration loader.

Each game lives in games/<game>/ with a config.yaml describing its engine,
languages, models, importer format, and categorization rules. This removes the
old hardcoded "games/diablo4" paths and lets a new game be added by dropping in
a folder + config — no code changes.

Cache and glossary are per (game, target-language):
    games/<game>/cache.<lang>.db
    games/<game>/glossary.yaml          (base / target_lang)
    games/<game>/glossary.<lang>.yaml   (other languages)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GAMES_DIR = PROJECT_ROOT / "games"

# Sensible defaults so a minimal config.yaml still works.
_DEFAULT_CATEGORY_PATTERNS = [
    ["achievement", "achievement"], ["quest", "quest"], ["item", "item"],
    ["affix", "item_affix"], ["power", "skill"], ["ability", "skill"],
    ["class_", "class"], ["monster", "monster"], ["npc", "npc_dialog"],
    ["dialog", "npc_dialog"], ["ui", "ui"], ["menu", "ui"], ["lore", "lore"],
]
_DEFAULT_PRIORITY_CATEGORIES = [
    "item", "quest", "skill", "npc_dialog", "item_affix",
    "ui", "class", "achievement", "lore", "monster", "other",
]


@dataclass
class GameConfig:
    game: str
    root: Path
    engine: str = "unknown"
    source_lang: str = "en"
    target_lang: str = "th"
    model_batch: str = "scb10x/llama3.1-typhoon2-8b-instruct"
    model_live: str = "scb10x/typhoon-translate1.5-4b"
    importer: dict = field(default_factory=lambda: {"format": "tsv", "columns": {}})
    category_patterns: list = field(default_factory=lambda: list(_DEFAULT_CATEGORY_PATTERNS))
    dropped_files: set = field(default_factory=set)
    priority_categories: set = field(default_factory=lambda: set(_DEFAULT_PRIORITY_CATEGORIES))
    raw: dict = field(default_factory=dict)

    # ---- loader ----
    @classmethod
    def load(cls, game: str, lang: str | None = None) -> "GameConfig":
        root = GAMES_DIR / game
        cfg_path = root / "config.yaml"
        data: dict = {}
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        target = lang or data.get("target_lang", "th")
        # Per-language model overrides: models: {zh: {batch:..., live:...}}
        lang_models = (data.get("models", {}) or {}).get(target, {})
        cfg = cls(
            game=game,
            root=root,
            engine=data.get("engine", "unknown"),
            source_lang=data.get("source_lang", "en"),
            target_lang=target,
            model_batch=lang_models.get("batch", data.get("model_batch", cls.model_batch)),
            model_live=lang_models.get("live", data.get("model_live", cls.model_live)),
            importer=data.get("importer", {"format": "tsv", "columns": {}}),
            category_patterns=[tuple(p) for p in data.get("category_patterns", _DEFAULT_CATEGORY_PATTERNS)],
            dropped_files=set(data.get("dropped_files", [])),
            priority_categories=set(data.get("priority_categories", _DEFAULT_PRIORITY_CATEGORIES)),
            raw=data,
        )
        return cfg

    # ---- path helpers ----
    @property
    def extracted_dir(self) -> Path:
        return self.root / "extracted"

    @property
    def translations_json(self) -> Path:
        return self.extracted_dir / "translations.json"

    @property
    def filtered_json(self) -> Path:
        return self.extracted_dir / "filtered_input.json"

    def cache_db(self, lang: str | None = None) -> Path:
        """Per-language cache. Falls back to legacy cache.db if the
        language-suffixed file doesn't exist yet (back-compat)."""
        lang = lang or self.target_lang
        p = self.root / f"cache.{lang}.db"
        legacy = self.root / "cache.db"
        if not p.exists() and legacy.exists():
            return legacy
        return p

    def glossary_path(self, lang: str | None = None) -> Path:
        """glossary.<lang>.yaml if present, else base glossary.yaml."""
        lang = lang or self.target_lang
        specific = self.root / f"glossary.{lang}.yaml"
        return specific if specific.exists() else self.root / "glossary.yaml"

    def categorize(self, filename: str) -> str:
        low = (filename or "").lower()
        for pattern, category in self.category_patterns:
            if pattern in low:
                return category
        return "other"
