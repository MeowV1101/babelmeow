"""
3-layer translation matcher for OCR text → cached Thai translation.

Layers (fastest first):
  1. EXACT      — dict lookup on raw text
  2. NORMALIZED — dict lookup after whitespace/case/punct normalization
  3. FUZZY      — rapidfuzz similarity over normalized keys (handles OCR errors)

Loads the entire cache into memory at startup for speed.
Reloadable so it picks up new entries the batch/live-fallback adds.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process

from .template import TemplateIndex, has_content_placeholder


@dataclass
class MatchResult:
    th_text: str | None
    matched_en: str | None
    method: str          # "exact" | "normalized" | "fuzzy" | "template" | "miss"
    score: float         # 100 for exact/normalized/template, <100 for fuzzy, 0 for miss


# Characters/markup to ignore when normalizing for comparison.
_WS_RE = re.compile(r"\s+")
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")          # {c_gold}, {LEVELAREA}, {icon:...}
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize(text: str) -> str:
    """Normalize text for fuzzy comparison: drop markup, lowercase, collapse ws."""
    t = _PLACEHOLDER_RE.sub(" ", text)
    t = t.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


class Matcher:
    def __init__(
        self,
        db_path: str | Path,
        fuzzy_cutoff: float = 85.0,
        fuzzy_min_len: int = 6,
        length_ratio_min: float = 0.6,
    ):
        self.db_path = Path(db_path)
        self.fuzzy_cutoff = fuzzy_cutoff
        self.fuzzy_min_len = fuzzy_min_len  # don't fuzzy-match very short strings (false hits)
        self.length_ratio_min = length_ratio_min  # reject length-mismatched fuzzy hits
        self._lock = threading.Lock()

        # In-memory indexes
        self._exact: dict[str, str] = {}          # en_text -> th_text
        self._norm: dict[str, str] = {}           # normalized -> en_text
        self._norm_keys: list[str] = []           # for rapidfuzz candidate list
        self._len_buckets: dict[int, list[str]] = {}  # length -> norm keys
        self._templates = TemplateIndex()
        self._loaded_at = 0.0
        self.load()

    def load(self) -> int:
        """(Re)load all translations from the cache DB into memory."""
        exact: dict[str, str] = {}
        norm: dict[str, str] = {}
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT en_text, th_text FROM translations WHERE th_text IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()

        for r in rows:
            en, th = r["en_text"], r["th_text"]
            exact[en] = th
            # Entries with content placeholders ({MONSTER}, {floor}, ...) are
            # reserved for the TEMPLATE layer — exclude from normalized/fuzzy so
            # they can't be returned with an unfilled placeholder.
            if has_content_placeholder(en):
                continue
            n = normalize(en)
            if n and n not in norm:   # keep first; collisions are rare
                norm[n] = en

        # Bucket normalized keys by length for fast fuzzy candidate selection.
        # Fuzzy only compares strings of similar length, so we never scan all 96k.
        buckets: dict[int, list[str]] = {}
        for k in norm.keys():
            buckets.setdefault(len(k), []).append(k)

        with self._lock:
            self._exact = exact
            self._norm = norm
            self._norm_keys = list(norm.keys())
            self._len_buckets = buckets
            self._templates.build(exact)
            self._loaded_at = time.time()
        return len(exact)

    def _fuzzy_candidates(self, n: str) -> list[str]:
        """Norm keys whose length is within tolerance of n (for fast fuzzy)."""
        ln = len(n)
        tol = max(3, int(ln * 0.30))
        out: list[str] = []
        for length in range(ln - tol, ln + tol + 1):
            bucket = self._len_buckets.get(length)
            if bucket:
                out.extend(bucket)
        return out

    @property
    def template_count(self) -> int:
        return self._templates.count

    def _translate_value(self, value: str) -> str | None:
        """Re-translate a captured template value via exact/normalized only
        (no fuzzy/template — avoid recursion / latency)."""
        th = self._exact.get(value) or self._exact.get(value.strip())
        if th is not None:
            return th
        en = self._norm.get(normalize(value))
        return self._exact[en] if en is not None else None

    @property
    def size(self) -> int:
        return len(self._exact)

    def lookup(self, text: str) -> MatchResult:
        if not text or not text.strip():
            return MatchResult(None, None, "miss", 0.0)

        # 1. EXACT
        th = self._exact.get(text)
        if th is not None:
            return MatchResult(th, text, "exact", 100.0)

        # also try trimmed exact
        stripped = text.strip()
        th = self._exact.get(stripped)
        if th is not None:
            return MatchResult(th, stripped, "exact", 100.0)

        # 2. NORMALIZED
        n = normalize(text)
        if n:
            en = self._norm.get(n)
            if en is not None:
                return MatchResult(self._exact[en], en, "normalized", 100.0)

        # 3. TEMPLATE (dynamic strings: "Defeat the Butcher" -> "ปราบ บุชเชอร์")
        # Runs BEFORE fuzzy: templates are high-precision (anchored regex with
        # literal text), so they beat a partial fuzzy match like "Defeat the
        # Butcher" -> "The Butcher".
        tm = self._templates.match(text, translate_fn=self._translate_value)
        if tm is not None:
            th_filled, matched_en = tm
            return MatchResult(th_filled, matched_en, "template", 100.0)

        # 4. FUZZY (last resort before miss; skip very short — false positives)
        if n and len(n) >= self.fuzzy_min_len:
            candidates = self._fuzzy_candidates(n)
            # WRatio tolerates OCR errors well; the length guard below rejects its
            # substring false-positives (e.g. "...nonsense" matching "no").
            best = process.extractOne(
                n,
                candidates,
                scorer=fuzz.WRatio,
                score_cutoff=self.fuzzy_cutoff,
            ) if candidates else None
            if best:
                matched_norm, score, _ = best
                # Length guard: reject matches where the two strings differ a lot in
                # length (kills "zzxqwv nonsense" -> "no" style substring false hits).
                len_ratio = min(len(n), len(matched_norm)) / max(len(n), len(matched_norm))
                if len_ratio >= self.length_ratio_min:
                    en = self._norm[matched_norm]
                    return MatchResult(self._exact[en], en, "fuzzy", float(score))

        return MatchResult(None, None, "miss", 0.0)

    def add(self, en_text: str, th_text: str) -> None:
        """Add a new translation to the in-memory index (after live fallback)."""
        with self._lock:
            self._exact[en_text] = th_text
            n = normalize(en_text)
            if n and n not in self._norm:
                self._norm[n] = en_text
                self._norm_keys.append(n)
