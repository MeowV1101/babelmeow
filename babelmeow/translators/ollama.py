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


SYSTEM_PROMPT_TEMPLATE = """You are translating Diablo IV (a dark fantasy ARPG) from English to Thai.

STYLE GUIDE (สำคัญมาก):
- ใช้สำนวนวรรณกรรม dark fantasy แบบเกม MMORPG ภาษาไทย ไม่ใช่ภาษาพูดทั่วไป
- คำว่า "ฆ่า" → ใช้ "สังหาร" ฟังขลังกว่า
- คำว่า "แม่" → ใช้ "มารดา" สำหรับ lore/item
- คำว่า "ผิดกฎหมาย" → ห้าม ใช้ "ต้องห้าม" หรือ "อาถรรพ์"
- item affix แบบ "+X to Y" → ตัด "to/ถึง" ออก เช่น "+12 พลังชีวิตสูงสุด"
- ไม่ใส่ space เกินก่อน proper nouns
- เก็บ damage number และ placeholder {{0}}, %s ไว้ตามเดิม

GLOSSARY (ห้ามแปลเป็นอื่น):
{glossary}

FEW-SHOT EXAMPLES:
EN: Kill the Skeleton King
TH: สังหารราชาโครงกระดูก

EN: +25 to Strength
TH: +25 พลังกาย

EN: The forgotten gods stir in their slumber.
TH: เหล่าทวยเทพที่ถูกลืมกำลังเริ่มขยับในนิทรา

EN: You dealt 500 damage to Goblin
TH: คุณสร้างความเสียหาย 500 หน่วยต่อก็อบลิน

OUTPUT RULES:
- Output ONLY the Thai translation
- No quotes, no English, no explanation, no notes
- One line for short, multi-line OK for paragraphs
"""


class OllamaTranslator:
    def __init__(
        self,
        model: str = "scb10x/llama3.1-typhoon2-8b-instruct",
        host: str = "http://localhost:11434",
        temperature: float = 0.15,
        num_predict: int = 250,
        timeout: int = 180,
    ):
        self.model = model
        self.host = host
        self.url = f"{host}/api/generate"
        self.temperature = temperature
        self.num_predict = num_predict
        self.timeout = timeout

    def build_system(self, glossary_block: str) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(glossary=glossary_block)

    def translate(self, en_text: str, system: str) -> TranslationResult:
        payload = {
            "model": self.model,
            "prompt": f"Translate to Thai:\n{en_text}",
            "system": system,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
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
