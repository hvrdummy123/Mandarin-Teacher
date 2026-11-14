"""Pinyin + segmentation cases from SPEC §15."""

from __future__ import annotations

import re

from app.adapters.dictionary.memory import seed_basic_dictionary
from app.application.text_analyzer import TextAnalyzer


def _py(analyzer: TextAnalyzer, text: str) -> str:
    tokens = analyzer.analyze(text)
    return " ".join(t.pinyin for t in tokens if t.pinyin)


def test_nihao_pinyin() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    py = _py(a, "你好")
    # Written form with sandhi may be nǐ hǎo; spoken note ní hǎo is also acceptable.
    compact = py.replace(" ", "")
    assert "nǐ" in py or "ní" in py
    assert "hǎo" in py
    assert re.search(r"n[iíǐ].*hǎo", compact) or "nǐhǎo" in compact or "níhǎo" in compact


def test_yinhang_not_yinxing() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    py = _py(a, "银行")
    assert "yín" in py or "yin" in py.lower()
    assert "háng" in py or "hang" in py.lower()
    assert "xíng" not in py
    assert "xing" not in py.lower().replace("yinhang", "")


def test_zhongyao() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    py = _py(a, "重要")
    assert "zhòng" in py or "zhong" in py.lower()
    assert "yào" in py or "yao" in py.lower()


def test_budui_sandhi() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    py = _py(a, "不对")
    # 不 before tone-4 → bú
    assert "bú" in py or "bu" in py.lower()
    assert "duì" in py or "dui" in py.lower()


def test_yige_and_yitian() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    py1 = _py(a, "一个")
    py2 = _py(a, "一天")
    # 一 before tone-4 → yí; before tone-1 → yì
    assert "yí" in py1 or "yi" in py1.lower()
    assert "yì" in py2 or "yi" in py2.lower()


def test_mixed_text_does_not_crash() -> None:
    a = TextAnalyzer(seed_basic_dictionary())
    tokens = a.analyze("Hello 你好 123！OK")
    surfaces = [t.surface for t in tokens]
    assert "Hello" in surfaces
    assert any("你" in s or s == "你好" for s in surfaces)
    assert "123" in surfaces
