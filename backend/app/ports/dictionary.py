"""Dictionary lookup port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class DictEntry:
    simplified: str
    traditional: str
    pinyin: str
    definitions: list[str]


@runtime_checkable
class DictionaryRepo(Protocol):
    def lookup(self, word: str) -> list[DictEntry]:
        """Return entries for simplified or traditional form; empty if unknown."""
        ...

    def hsk_level(self, word: str) -> int | None: ...
