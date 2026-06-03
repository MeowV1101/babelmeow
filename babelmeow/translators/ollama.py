"""Ollama API client for batch translation."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests


@dataclass
class TranslationResult:
    en: str
    th: str
    elapsed_sec: float
    model: str
    warnings: list[str]


# Generic, language-agnostic skeleton. Language-specific parts (style, examples)
# come from the langpack (babelmeow/langpacks/<lang>.yaml). {{...}} are literal
# braces (this is a .format() template).
SYSTEM_PROMPT_TEMPLATE = """You are translating a dark fantasy ARPG video game from {source_name} to {target_name}.

═══════════════════════════════════════════════════════════════
🔒 GLOSSARY — MUST USE THESE EXACT TRANSLATIONS:
═══════════════════════════════════════════════════════════════
{glossary}

If you see ANY of the {source_name} words above in the input, you MUST use the
corresponding {target_name} term EXACTLY. Do NOT transliterate, do NOT translate
literally, do NOT create variations. Copy it character-by-character.

═══════════════════════════════════════════════════════════════
STYLE GUIDE:
═══════════════════════════════════════════════════════════════
{style}

🔴 CRITICAL — PRESERVE EXACTLY (do not translate, do not change):
- Color/markup tags: {{c_gold}}, {{c_red}}, {{/c}}, {{c_white}}, etc.
- Variable placeholders: {{LEVELAREA}}, {{NAME}}, {{s1}}, {{playerName}}, {{n0}}
- Format codes: %s, %d, %1$s, %2$d
- Icon refs: {{icon:Skull,2.5}}, {{icon:Region_Icon_Hell,2.5}}
- Brace expressions are ALWAYS kept as-is — copy character-by-character

═══════════════════════════════════════════════════════════════
EXAMPLES (match this style exactly):
═══════════════════════════════════════════════════════════════
{few_shot}

═══════════════════════════════════════════════════════════════
OUTPUT RULES:
═══════════════════════════════════════════════════════════════
- Output ONLY the {target_name} translation
- No quotes, no {source_name} (except glossary proper nouns kept as-is)
- No explanation, no notes
- Match the style of the examples above EXACTLY
"""


from ..langpack import LANG_NAMES, LangPack


class OllamaTranslator:
    def __init__(
        self,
        model: str = "scb10x/llama3.1-typhoon2-8b-instruct",
        host: str = "http://localhost:11434",
        temperature: float = 0.05,
        num_predict: int = 250,
        timeout: int = 180,
        target_lang: str = "th",
        source_lang: str = "en",
        langpack: LangPack | None = None,
    ):
        self.model = model
        self.host = host
        self.url = f"{host}/api/generate"
        self.temperature = temperature
        self.num_predict = num_predict
        self.timeout = timeout
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.langpack = langpack or LangPack.load(target_lang)
        self.source_name = LANG_NAMES.get(source_lang, source_lang)
        self.target_lang_name = self.langpack.name

    def build_system(self, glossary_block: str) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(
            glossary=glossary_block,
            source_name=self.source_name,
            target_name=self.target_lang_name,
            style=self.langpack.prompt_style or "- Use natural, fluent target-language phrasing.",
            few_shot=self.langpack.few_shot_block(self.source_name) or "(none)",
        )

    def translate(self, en_text: str, system: str) -> TranslationResult:
        payload = {
            "model": self.model,
            "prompt": f"Translate to {self.target_lang_name}:\n{en_text}",
            "system": system,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                # Cap context: our system prompt (~1500 tok) + input + output fits in 3072.
                # Keeps KV-cache small so 4 parallel slots stay within 16 GB VRAM.
                "num_ctx": 3072,
            },
        }
        start = time.time()
        resp = requests.post(self.url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        elapsed = time.time() - start
        th = resp.json()["response"].strip()
        return TranslationResult(
            en=en_text,
            th=th,
            elapsed_sec=elapsed,
            model=self.model,
            warnings=[],
        )
