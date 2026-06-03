"""
Language pack loader.

A langpack (babelmeow/langpacks/<lang>.yaml) holds everything language-specific
that used to be hardcoded for Thai:
  - name                 : human name injected into the prompt ("Thai")
  - prompt_style         : style-guide bullets for the system prompt
  - few_shot             : [{en, tgt}] examples
  - wrong_transliterations : {wrong: right} output fixes (PostProcessor)
  - semantic_traps       : [[src_regex, tgt_regex, name]] (PostProcessor)

Add a new target language = drop in a new <lang>.yaml. No code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

LANGPACK_DIR = Path(__file__).resolve().parent / "langpacks"

# Fallback human names if a langpack omits 'name'.
LANG_NAMES = {"th": "Thai", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
              "es": "Spanish", "fr": "French", "de": "German", "en": "English"}


@dataclass
class LangPack:
    lang: str
    name: str
    prompt_style: str = ""
    few_shot: list = field(default_factory=list)
    wrong_transliterations: dict = field(default_factory=dict)
    semantic_traps: list = field(default_factory=list)

    @classmethod
    def load(cls, lang: str) -> "LangPack":
        path = LANGPACK_DIR / f"{lang}.yaml"
        data: dict = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(
            lang=lang,
            name=data.get("name", LANG_NAMES.get(lang, lang)),
            prompt_style=data.get("prompt_style", "").strip(),
            few_shot=data.get("few_shot", []),
            wrong_transliterations=data.get("wrong_transliterations", {}),
            semantic_traps=data.get("semantic_traps", []),
        )

    def few_shot_block(self, source_name: str = "EN") -> str:
        """Format few-shot examples as 'SRC: ...\\nTGT: ...' blocks."""
        out = []
        for ex in self.few_shot:
            en = ex.get("en", "")
            tgt = ex.get("tgt", "")
            out.append(f"{source_name}: {en}\nTGT: {tgt}")
        return "\n\n".join(out)
