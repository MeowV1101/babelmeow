"""Post-process translations to enforce glossary and detect semantic errors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .glossary import Glossary


# Patterns we MUST preserve EXACTLY in the output (auto-restore if model strips them)
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}"),         # {NAME}, {LEVELAREA}, {s1}
    re.compile(r"\{c_[a-z]+\}"),                        # {c_gold}, {c_red}
    re.compile(r"\{/c\}"),                              # {/c} closing
    re.compile(r"\{icon:[^}]+\}"),                      # {icon:Skull,2.5}
    re.compile(r"%[\d]*\$?[a-z]"),                      # %s, %d, %1$s
]


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
    """Apply glossary enforcement and semantic checks to a raw translation.

    `lang` selects which language-specific rule set to use. Phase B loads
    wrong-transliteration / semantic-trap rules from a langpack; for now `th`
    uses the built-in constants (unchanged behavior), other langs use empty
    rule sets (glossary + placeholder checks still apply, which are language-
    agnostic)."""

    def __init__(self, glossary: Glossary, lang: str = "th",
                 wrong_transliterations: dict | None = None,
                 semantic_traps: list | None = None):
        self.glossary = glossary
        self.lang = lang
        # Rule precedence: explicit args > langpack yaml > built-in TH constants.
        from ..langpack import LangPack
        lp = LangPack.load(lang)
        if wrong_transliterations is not None:
            self.wrong = wrong_transliterations
        elif lp.wrong_transliterations:
            self.wrong = lp.wrong_transliterations
        else:
            self.wrong = KNOWN_WRONG_TRANSLITERATIONS if lang == "th" else {}
        if semantic_traps is not None:
            self.traps = semantic_traps
        elif lp.semantic_traps:
            self.traps = [tuple(t) for t in lp.semantic_traps]
        else:
            self.traps = SEMANTIC_TRAPS if lang == "th" else []

    def process(self, en_text: str, th_text: str) -> ProcessResult:
        result = ProcessResult(original=th_text, corrected=th_text)

        # 1. Apply known wrong transliteration fixes
        for wrong, right in self.wrong.items():
            if wrong in result.corrected:
                result.corrected = result.corrected.replace(wrong, right)
                result.fixes.append(f"{wrong} → {right}")

        # 2. Enforce glossary — for each EN term in source, ensure TH term in output
        # If EN term still in output verbatim (untranslated), auto-replace with TH.
        for en_term, th_term in self.glossary.find_en_in(en_text):
            if th_term in result.corrected:
                continue
            # English term is leaked through untranslated → force replace
            # Use word boundary on alpha chars to avoid partial replacement
            pattern = re.compile(r"\b" + re.escape(en_term) + r"\b")
            if pattern.search(result.corrected):
                result.corrected = pattern.sub(th_term, result.corrected)
                result.fixes.append(f"{en_term} → {th_term} (auto-replaced)")
            else:
                # Glossary term missing and no English remnant — likely paraphrased
                result.warnings.append(
                    f"Glossary miss: '{en_term}' should yield '{th_term}'"
                )
                result.needs_review = True

        # 3. Detect semantic traps
        for en_pattern, th_pattern, name in self.traps:
            if re.search(en_pattern, en_text, re.IGNORECASE) and re.search(
                th_pattern, result.corrected
            ):
                result.warnings.append(f"Semantic trap: {name}")
                result.needs_review = True

        # 4. Auto-restore placeholders that the model "translated" by mistake
        # Strategy: if EN placeholder X is missing in output, find a foreign-looking
        # {something} in output that isn't in EN, and swap it back.
        en_placeholders = re.findall(r"\{[^{}]+\}", en_text)
        for en_ph in en_placeholders:
            if en_ph in result.corrected:
                continue
            # Missing — try to find a translated version to swap
            out_placeholders = re.findall(r"\{[^{}]+\}", result.corrected)
            for out_ph in out_placeholders:
                if out_ph not in en_text:
                    # Likely a translated placeholder — swap back
                    result.corrected = result.corrected.replace(out_ph, en_ph, 1)
                    result.fixes.append(f"{out_ph} → {en_ph} (placeholder restored)")
                    break

        # 5. Verify placeholders/tags preserved — flag remaining missing
        for pat in PLACEHOLDER_PATTERNS:
            src_tags = pat.findall(en_text)
            out_tags = pat.findall(result.corrected)
            for tag in src_tags:
                if src_tags.count(tag) > out_tags.count(tag):
                    result.warnings.append(f"Missing placeholder/tag: {tag}")
                    result.needs_review = True

        # 5. Sanity checks
        # Empty or too-short output
        if len(result.corrected) < 2:
            result.warnings.append("Output suspiciously short")
            result.needs_review = True

        # Output still contains English (likely failed translation)
        # — but allow proper-noun retention from glossary and placeholder content
        # Strip placeholders before checking
        stripped = result.corrected
        for pat in PLACEHOLDER_PATTERNS:
            stripped = pat.sub("", stripped)

        en_in_th = len(re.findall(r"[A-Za-z]{4,}", stripped))
        if en_in_th > 0:
            glossary_keys = set(self.glossary.terms.keys())
            words_in_output = set(re.findall(r"[A-Za-z]+", stripped))
            non_glossary = words_in_output - glossary_keys
            if non_glossary:
                result.warnings.append(
                    f"English remnant in output: {non_glossary}"
                )
                result.needs_review = True

        return result
