"""Post-process translations to enforce glossary and detect semantic errors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .glossary import Glossary


# Known wrong transliterations → correct ones.
# Populate this as you discover model mistakes during testing.
KNOWN_WRONG_TRANSLITERATIONS: dict[str, str] = {
    # Nephalem variants
    "นีเฟลีมี": "เนฟาเลม",
    "นีเฟลีม": "เนฟาเลม",
    "เนเฟเลม": "เนฟาเลม",
    "นีฟาเลม": "เนฟาเลม",
    # Lilith variants
    "ลีลิธ": "ลิลิธ",
    "ลีลิท": "ลิลิธ",
    # Sanctuary variants
    "แซงค์ชัวร์รี": "แซงค์ชัวรี",
    "แซงทัวรี": "แซงค์ชัวรี",
    # Butcher — common literal translations
    "ช่างเนื้อ": "บุชเชอร์",
    "คนเลี้ยงสัตว์": "บุชเชอร์",
    "คนฆ่าสัตว์": "บุชเชอร์",
    "คนชำแหละ": "บุชเชอร์",
    # Skeleton Warrior — when full phrase appears wrong
    "ผู้พิชิตโครงกระดูก": "โครงกระดูกนักรบ",
    "นักรบโครงกระดูก": "โครงกระดูกนักรบ",
}

# Semantic error patterns — pairs of (en_keyword, wrong_th_pattern, severity)
# These flag for human review, don't auto-fix because context matters.
SEMANTIC_TRAPS = [
    # "torrent of fire" should be flame/fire, not water
    (r"\bfire\b|\bflame\b", r"กระแสน้ำ|น้ำไฟ|สายน้ำ", "fire/water confusion"),
    # "lightning" should be electric, not fire
    (r"\blightning\b|\bthunder\b", r"เพลิง|ไฟลุก", "lightning/fire confusion"),
    # "frost"/"ice" should be cold, not heat
    (r"\bfrost\b|\bice\b|\bcold\b", r"ร้อน|เพลิง", "ice/heat confusion"),
]


@dataclass
class ProcessResult:
    original: str
    corrected: str
    fixes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    needs_review: bool = False


class PostProcessor:
    """Apply glossary enforcement and semantic checks to a raw translation."""

    def __init__(self, glossary: Glossary):
        self.glossary = glossary

    def process(self, en_text: str, th_text: str) -> ProcessResult:
        result = ProcessResult(original=th_text, corrected=th_text)

        # 1. Apply known wrong transliteration fixes
        for wrong, right in KNOWN_WRONG_TRANSLITERATIONS.items():
            if wrong in result.corrected:
                result.corrected = result.corrected.replace(wrong, right)
                result.fixes.append(f"{wrong} → {right}")

        # 2. Enforce glossary — for each EN term in source, ensure TH term in output
        for en_term, th_term in self.glossary.find_en_in(en_text):
            if th_term not in result.corrected:
                # Glossary term missing → flag for review
                result.warnings.append(
                    f"Glossary miss: '{en_term}' should yield '{th_term}'"
                )
                result.needs_review = True

        # 3. Detect semantic traps
        for en_pattern, th_pattern, name in SEMANTIC_TRAPS:
            if re.search(en_pattern, en_text, re.IGNORECASE) and re.search(
                th_pattern, result.corrected
            ):
                result.warnings.append(f"Semantic trap: {name}")
                result.needs_review = True

        # 4. Sanity checks
        # Extra leading spaces before Thai characters
        if re.search(r"[ฯ-๛] +[ฯ-๛]", result.corrected):
            # Try fix common case: " " between Thai words (heuristic)
            pass  # leave for human review

        # Empty or too-short output
        if len(result.corrected) < 2:
            result.warnings.append("Output suspiciously short")
            result.needs_review = True

        # Output still contains English (likely failed translation)
        # — but allow proper-noun retention from glossary
        en_in_th = len(re.findall(r"[A-Za-z]{4,}", result.corrected))
        if en_in_th > 0:
            # Check if all English remnants are glossary terms
            glossary_keys = set(self.glossary.terms.keys())
            words_in_output = set(re.findall(r"[A-Za-z]+", result.corrected))
            non_glossary = words_in_output - glossary_keys
            if non_glossary:
                result.warnings.append(
                    f"English remnant in output: {non_glossary}"
                )

        return result
