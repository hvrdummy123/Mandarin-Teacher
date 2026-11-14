"""Dictionary lookup behaviour."""

from __future__ import annotations

from app.adapters.dictionary.memory import seed_basic_dictionary


def test_common_word_lookup() -> None:
    d = seed_basic_dictionary()
    entries = d.lookup("你好")
    assert entries
    assert "hello" in entries[0].definitions[0].lower()


def test_unknown_returns_empty() -> None:
    d = seed_basic_dictionary()
    assert d.lookup("䶮䶮") == []


def test_traditional_lookup() -> None:
    d = seed_basic_dictionary()
    entries = d.lookup("銀行")
    assert entries
    assert entries[0].simplified == "银行"


def test_hsk_level() -> None:
    d = seed_basic_dictionary()
    assert d.hsk_level("银行") == 2
    assert d.hsk_level("䶮䶮") is None
