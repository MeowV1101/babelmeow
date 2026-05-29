"""
Template matching for dynamic in-game text (Phase 5).

Game strings contain placeholders the engine fills at runtime:
    cache:  "Defeat the {MONSTER}"  ->  "ปราบ {MONSTER}"
    screen: "Defeat the Butcher"     (engine substituted {MONSTER})
    OCR:    "Defeat the Butcher"

This module:
    1. builds regex templates from cache entries that have CONTENT placeholders
       (markup-only placeholders like {c_gold}/{/c} are ignored — OCR never sees them)
    2. matches OCR text against templates, capturing the variable parts
    3. substitutes captured values into the Thai template, re-translating
       text values (e.g. Butcher -> บุชเชอร์) but leaving numbers as-is

Indexed by first literal word for speed; placeholder-initial templates go to a
small always-scan bucket.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Placeholders that are pure display markup — strip, don't treat as variables.
_MARKUP_RE = re.compile(r"\{c_[^{}]*\}|\{/c\}")
# Any placeholder.
_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
# A captured value that is "just a number/count" — keep verbatim, don't translate.
_NUMERIC_RE = re.compile(r"^[\d.,%/:\s\-]+$")

# Minimum literal (non-placeholder) characters for a template to be safe.
# Prevents over-generic templates like "{MONSTER}" -> "^(.+)$" matching everything.
_MIN_LITERAL_CHARS = 4


@dataclass
class Template:
    regex: re.Pattern
    names: list[str]       # ordered content-placeholder names, e.g. ["MONSTER","LEFT"]
    th_text: str           # Thai template, still containing {NAME} placeholders
    en_text: str           # original EN (for debugging)


def _strip_markup(text: str) -> str:
    return _MARKUP_RE.sub("", text)


def has_content_placeholder(text: str) -> bool:
    """True if text has a non-markup placeholder (reserved for template layer)."""
    return bool(_content_placeholders(text))


def _content_placeholders(text: str) -> list[str]:
    """Return content placeholder names (markup excluded), in order."""
    out = []
    for m in _PLACEHOLDER_RE.finditer(text):
        tok = m.group(0)
        if _MARKUP_RE.fullmatch(tok):
            continue
        out.append(tok[1:-1])  # strip { }
    return out


def _first_literal_word(en_no_markup: str) -> str | None:
    """First alphanumeric word that is NOT inside a placeholder (for indexing)."""
    # Replace placeholders with a sentinel space, then take first word.
    stripped = _PLACEHOLDER_RE.sub(" ", en_no_markup)
    m = re.search(r"[A-Za-z0-9]+", stripped)
    return m.group(0).lower() if m else None


def _build_regex(en_no_markup: str) -> tuple[re.Pattern | None, list[str], int]:
    """
    Build a case-insensitive regex from EN (markup already stripped).
    Content placeholders -> non-greedy capture groups. Returns (regex, names, literal_char_count).
    """
    names: list[str] = []
    parts: list[str] = []
    literal_chars = 0
    last = 0
    for m in _PLACEHOLDER_RE.finditer(en_no_markup):
        literal = en_no_markup[last:m.start()]
        literal_chars += len(literal.strip())
        parts.append(re.escape(literal))
        names.append(m.group(0)[1:-1])
        parts.append(r"(.+?)")
        last = m.end()
    tail = en_no_markup[last:]
    literal_chars += len(tail.strip())
    parts.append(re.escape(tail))

    if not names:
        return None, [], literal_chars  # no content placeholder -> not a template

    pattern = "^" + "".join(parts) + "$"
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None, [], literal_chars
    return rx, names, literal_chars


class TemplateIndex:
    def __init__(self):
        self._by_word: dict[str, list[Template]] = {}
        self._no_prefix: list[Template] = []
        self.count = 0

    def build(self, entries: dict[str, str]) -> int:
        """entries: {en_text: th_text}. Build templates from those with placeholders."""
        by_word: dict[str, list[Template]] = {}
        no_prefix: list[Template] = []
        count = 0

        for en, th in entries.items():
            if "{" not in en:
                continue
            en_nm = _strip_markup(en)
            content = _content_placeholders(en)
            if not content:
                continue  # markup-only -> handled by normalize layer
            rx, names, literal_chars = _build_regex(en_nm)
            if rx is None or literal_chars < _MIN_LITERAL_CHARS:
                continue  # too generic / unsafe
            tmpl = Template(regex=rx, names=names, th_text=th, en_text=en)

            anchor = _first_literal_word(en_nm)
            if anchor:
                by_word.setdefault(anchor, []).append(tmpl)
            else:
                no_prefix.append(tmpl)
            count += 1

        self._by_word = by_word
        self._no_prefix = no_prefix
        self.count = count
        return count

    def match(self, text: str, translate_fn=None) -> tuple[str, str] | None:
        """
        Try to match text against templates.
        Returns (thai_filled, matched_en_template) or None.
        translate_fn(value) -> thai|None  is used to re-translate captured text
        values (monster names etc); numbers are kept verbatim.
        """
        t = _strip_markup(text).strip()
        if not t:
            return None

        first = _first_literal_word(t)
        candidates = list(self._by_word.get(first, [])) if first else []
        candidates.extend(self._no_prefix)
        if not candidates:
            return None

        for tmpl in candidates:
            m = tmpl.regex.match(t)
            if not m:
                continue
            values = dict(zip(tmpl.names, m.groups()))
            th = tmpl.th_text
            for name, val in values.items():
                val = (val or "").strip()
                if not _NUMERIC_RE.match(val) and translate_fn:
                    tr = translate_fn(val)
                    if tr:
                        val = tr
                th = th.replace("{" + name + "}", val)
            # strip any leftover markup in the TH template for clean display
            th = _strip_markup(th)
            return th, tmpl.en_text
        return None
