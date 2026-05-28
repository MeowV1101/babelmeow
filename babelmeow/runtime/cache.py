"""SQLite-backed translation cache.

Schema:
    translations(
        en_text TEXT PRIMARY KEY,
        th_text TEXT,
        model TEXT,
        category TEXT,
        verified INT DEFAULT 0,
        needs_review INT DEFAULT 0,
        elapsed_ms INT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        warnings TEXT
    )

Designed for:
- Concurrent reads (lookup during batch and runtime)
- Single writer (batch translator)
- WAL mode for safety + perf
- Resume — INSERT OR IGNORE preserves prior translations
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    en_text TEXT PRIMARY KEY,
    th_text TEXT NOT NULL,
    model TEXT,
    category TEXT,
    verified INTEGER DEFAULT 0,
    needs_review INTEGER DEFAULT 0,
    elapsed_ms INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    warnings TEXT
);

CREATE INDEX IF NOT EXISTS idx_translations_category ON translations(category);
CREATE INDEX IF NOT EXISTS idx_translations_review ON translations(needs_review);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass
class CacheEntry:
    en_text: str
    th_text: str
    model: str | None = None
    category: str | None = None
    verified: bool = False
    needs_review: bool = False
    elapsed_ms: int | None = None
    warnings: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TranslationCache:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ───── lookup ─────

    def get(self, en_text: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT th_text FROM translations WHERE en_text = ?",
                (en_text,),
            ).fetchone()
        return row["th_text"] if row else None

    def has(self, en_text: str) -> bool:
        return self.get(en_text) is not None

    def get_many(self, en_texts: list[str]) -> dict[str, str]:
        """Bulk lookup for batch hits/miss check."""
        if not en_texts:
            return {}
        placeholders = ",".join("?" * len(en_texts))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT en_text, th_text FROM translations WHERE en_text IN ({placeholders})",
                en_texts,
            ).fetchall()
        return {r["en_text"]: r["th_text"] for r in rows}

    # ───── write ─────

    def put(self, entry: CacheEntry) -> None:
        now = _now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO translations
                    (en_text, th_text, model, category, verified, needs_review,
                     elapsed_ms, created_at, updated_at, warnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(en_text) DO UPDATE SET
                    th_text=excluded.th_text,
                    model=excluded.model,
                    category=excluded.category,
                    needs_review=excluded.needs_review,
                    elapsed_ms=excluded.elapsed_ms,
                    updated_at=excluded.updated_at,
                    warnings=excluded.warnings
                """,
                (
                    entry.en_text,
                    entry.th_text,
                    entry.model,
                    entry.category,
                    int(entry.verified),
                    int(entry.needs_review),
                    entry.elapsed_ms,
                    now,
                    now,
                    entry.warnings,
                ),
            )

    def put_many(self, entries: list[CacheEntry]) -> None:
        if not entries:
            return
        now = _now()
        rows = [
            (
                e.en_text,
                e.th_text,
                e.model,
                e.category,
                int(e.verified),
                int(e.needs_review),
                e.elapsed_ms,
                now,
                now,
                e.warnings,
            )
            for e in entries
        ]
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO translations
                    (en_text, th_text, model, category, verified, needs_review,
                     elapsed_ms, created_at, updated_at, warnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(en_text) DO UPDATE SET
                    th_text=excluded.th_text,
                    updated_at=excluded.updated_at
                """,
                rows,
            )

    # ───── stats ─────

    def stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM translations").fetchone()["n"]
            review = conn.execute(
                "SELECT COUNT(*) AS n FROM translations WHERE needs_review=1"
            ).fetchone()["n"]
            by_cat = conn.execute(
                "SELECT category, COUNT(*) AS n FROM translations GROUP BY category"
            ).fetchall()
            avg_ms = conn.execute(
                "SELECT AVG(elapsed_ms) AS avg FROM translations WHERE elapsed_ms IS NOT NULL"
            ).fetchone()["avg"] or 0
        return {
            "total": total,
            "needs_review": review,
            "avg_elapsed_ms": round(avg_ms),
            "by_category": {r["category"]: r["n"] for r in by_cat},
        }

    def existing_en_texts(self) -> set[str]:
        """Return the set of EN texts already translated — used for resume."""
        with self._connect() as conn:
            rows = conn.execute("SELECT en_text FROM translations").fetchall()
        return {r["en_text"] for r in rows}
