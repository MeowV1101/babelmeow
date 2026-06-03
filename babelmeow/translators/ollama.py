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


SYSTEM_PROMPT_TEMPLATE = """You are translating Diablo IV (dark fantasy ARPG) from English to Thai.

═══════════════════════════════════════════════════════════════
🔒 GLOSSARY — MUST USE THESE EXACT TRANSLATIONS (ห้ามแปลเป็นอื่นเด็ดขาด):
═══════════════════════════════════════════════════════════════
{glossary}

If you see ANY of the English words above in the input, you MUST use the
corresponding Thai term EXACTLY. Do NOT transliterate, do NOT translate
literally, do NOT create variations. Copy the Thai term character-by-character.

═══════════════════════════════════════════════════════════════
STYLE GUIDE:
═══════════════════════════════════════════════════════════════
- ใช้สำนวนวรรณกรรม dark fantasy แบบเกม MMORPG ภาษาไทย ไม่ใช่ภาษาพูดทั่วไป
- "ฆ่า" → ใช้ "สังหาร" ฟังขลังกว่า
- "แม่" → ใช้ "มารดา" สำหรับ lore/item
- "ผิดกฎหมาย" → ห้าม ใช้ "ต้องห้าม" หรือ "อาถรรพ์"
- item affix "+X to Y" → ตัด "to/ถึง" ออก เช่น "+12 พลังชีวิตสูงสุด"
- ไม่ใส่ space เกินก่อน proper nouns
- เก็บ damage number และ placeholder {{0}}, %s ไว้ตามเดิม

🔴 CRITICAL — PRESERVE EXACTLY (ห้ามแปล ห้ามแก้):
- Color/markup tags: {{c_gold}}, {{c_red}}, {{/c}}, {{c_white}}, etc.
- Variable placeholders: {{LEVELAREA}}, {{NAME}}, {{s1}}, {{playerName}}, {{n0}}
- Format codes: %s, %d, %1$s, %2$d
- Icon refs: {{icon:Skull,2.5}}, {{icon:Region_Icon_Hell,2.5}}
- Brace expressions are ALWAYS kept as-is — copy character-by-character

Example:
EN: "{{c_gold}}Right-click to learn{{/c}} a recipe in {{LEVELAREA}}"
TH: "{{c_gold}}คลิกขวาเพื่อเรียนรู้{{/c}}สูตรใน {{LEVELAREA}}"

═══════════════════════════════════════════════════════════════
GLOSSARY-MATCHED EXAMPLES (เลียนแบบรูปแบบนี้):
═══════════════════════════════════════════════════════════════
EN: Slay the Butcher
TH: สังหารบุชเชอร์

EN: The Nephalem are powerful beings.
TH: เนฟาเลมเป็นผู้ทรงพลัง

EN: Lilith has returned to Sanctuary.
TH: ลิลิธกลับมาที่แซงค์ชัวรี

EN: You dealt 500 damage to Skeleton Warrior
TH: คุณสร้างความเสียหาย 500 หน่วยต่อโครงกระดูกนักรบ

EN: +25 to Strength
TH: +25 พลังกาย

EN: The forgotten gods stir in their slumber.
TH: เหล่าทวยเทพที่ถูกลืมกำลังเริ่มขยับในนิทรา

═══════════════════════════════════════════════════════════════
OUTPUT RULES:
═══════════════════════════════════════════════════════════════
- Output ONLY the Thai translation
- No quotes, no English (except glossary proper nouns kept as-is)
- No explanation, no notes
- Match the style of the few-shot examples above EXACTLY
"""


# ISO code -> human language name used in the prompt directive.
LANG_NAMES = {"th": "Thai", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
              "es": "Spanish", "fr": "French", "de": "German", "en": "English"}


class OllamaTranslator:
    def __init__(
        self,
        model: str = "scb10x/llama3.1-typhoon2-8b-instruct",
        host: str = "http://localhost:11434",
        temperature: float = 0.05,
        num_predict: int = 250,
        timeout: int = 180,
        target_lang: str = "th",
    ):
        self.model = model
        self.host = host
        self.url = f"{host}/api/generate"
        self.temperature = temperature
        self.num_predict = num_predict
        self.timeout = timeout
        self.target_lang = target_lang
        self.target_lang_name = LANG_NAMES.get(target_lang, target_lang)

    def build_system(self, glossary_block: str) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(glossary=glossary_block)

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
