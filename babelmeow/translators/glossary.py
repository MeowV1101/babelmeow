"""Glossary loader and lookup."""

from __future__ import annotations

from pathlib import Path

import yaml


class Glossary:
    """
    Loads a YAML glossary file and provides lookup utilities.

    Layout:
        _meta: { ... }
        section_name: { EN: TH, EN: TH, ... }
        another_section: { ... }
    """

    def __init__(self, terms: dict[str, str], meta: dict | None = None):
        self.terms = terms
        self.meta = meta or {}

    @classmethod
    def from_yaml(cls, path: str | Path) -> Glossary:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        meta = raw.pop("_meta", {})
        terms: dict[str, str] = {}
        for section, mapping in raw.items():
            if isinstance(mapping, dict):
                terms.update(mapping)
        return cls(terms=terms, meta=meta)

    def __len__(self) -> int:
        return len(self.terms)

    def __getitem__(self, key: str) -> str | None:
        return self.terms.get(key)

    def find_en_in(self, text: str) -> list[tuple[str, str]]:
        """Return list of (en_term, th_term) where en_term appears in text."""
        return [
            (en, th)
            for en, th in self.terms.items()
            if en in text
        ]

    def to_prompt_block(self, sections: int = 80) -> str:
        """Format as a glossary block for system prompts."""
        items = list(self.terms.items())[:sections]
        return "\n".join(f"- {en} = {th}" for en, th in items)
