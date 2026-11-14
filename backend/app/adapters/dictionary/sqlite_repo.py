"""CC-CEDICT + HSK lookups against data/dictionary.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.ports.dictionary import DictEntry


class CedictSqliteRepo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        if self._conn is not None:
            return
        if not self.path.is_file():
            raise FileNotFoundError(f"dictionary missing: {self.path}")
        self._conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    @property
    def conn(self) -> sqlite3.Connection:
        self.connect()
        assert self._conn is not None
        return self._conn

    def lookup(self, word: str) -> list[DictEntry]:
        if not word:
            return []
        rows = self.conn.execute(
            "SELECT simplified, traditional, pinyin, definitions FROM cedict "
            "WHERE simplified = ? OR traditional = ? LIMIT 8",
            (word, word),
        ).fetchall()
        out: list[DictEntry] = []
        for row in rows:
            defs = [d.strip() for d in str(row["definitions"]).split(";") if d.strip()]
            out.append(
                DictEntry(
                    simplified=row["simplified"],
                    traditional=row["traditional"],
                    pinyin=row["pinyin"],
                    definitions=defs,
                )
            )
        return out

    def hsk_level(self, word: str) -> int | None:
        row = self.conn.execute("SELECT level FROM hsk WHERE word = ?", (word,)).fetchone()
        return int(row["level"]) if row else None

    def words_by_hsk_then_freq(self, limit: int = 12000) -> list[str]:
        """HSK-ranked word list for level vocabulary cutoffs."""
        rows = self.conn.execute(
            "SELECT word FROM hsk ORDER BY level ASC, word ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["word"] for r in rows]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
