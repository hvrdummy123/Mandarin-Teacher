"""Level policy: vocabulary size, tiers, reply post-check."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import lru_cache

from app.config import REPO_ROOT

_HAN = re.compile(r"[\u4e00-\u9fff]+")
# Latin capitals, or Chinese place-ish names that end with a toponym suffix.
_PROPER = re.compile(r"^[A-Z][a-zA-Z]+$|^[\u4e00-\u9fff]{1,4}(?:市|省|县|区|路|站|镇|村)$")


@dataclass(frozen=True)
class LevelRules:
    level: int
    vocab_size: int
    max_sentence_chars: int
    speech_rate: float
    # Rough HSK band hint for prompts (1–6 / 7–9).
    hsk_band: int


def tier_for_level(level: int) -> int:
    level = max(1, min(100, level))
    return (level - 1) // 10 + 1


def level_for_tier(tier: int) -> int:
    tier = max(1, min(10, tier))
    return (tier - 1) * 10 + 1


def default_vocab_size(level: int) -> int:
    """Exponential growth ~150 at L1 to ~11000 at L100."""
    level = max(1, min(100, level))
    n1, n100 = 150.0, 11000.0
    if level == 1:
        return int(n1)
    ratio = (n100 / n1) ** (1 / 99)
    return int(round(n1 * (ratio ** (level - 1))))


def default_max_chars(level: int) -> int:
    return min(80, 12 + level // 2)


def default_speech_rate(level: int) -> float:
    # Slower at low levels.
    return max(0.7, min(1.1, 0.75 + level / 200))


def hsk_band_for_level(level: int) -> int:
    # Map 1–100 onto HSK-ish bands for prompt hints.
    if level <= 10:
        return 1
    if level <= 25:
        return 2
    if level <= 40:
        return 3
    if level <= 55:
        return 4
    if level <= 70:
        return 5
    if level <= 85:
        return 6
    return 7


@lru_cache
def _curve_overrides() -> dict[str, object]:
    path = REPO_ROOT / "backend" / "data" / "level_curve.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def rules_for_level(level: int) -> LevelRules:
    level = max(1, min(100, level))
    curve = _curve_overrides()
    levels = curve.get("levels") if isinstance(curve.get("levels"), dict) else {}
    override = levels.get(str(level)) if isinstance(levels, dict) else None
    vocab = default_vocab_size(level)
    max_chars = default_max_chars(level)
    rate = default_speech_rate(level)
    if isinstance(override, dict):
        vocab = int(override.get("vocab_size", vocab))
        max_chars = int(override.get("max_sentence_chars", max_chars))
        rate = float(override.get("speech_rate", rate))
    return LevelRules(
        level=level,
        vocab_size=vocab,
        max_sentence_chars=max_chars,
        speech_rate=rate,
        hsk_band=hsk_band_for_level(level),
    )


@dataclass(frozen=True)
class PostCheckResult:
    accepted: bool
    regenerated: bool
    out_of_level: tuple[str, ...]
    share: float
    text: str


def chinese_words(text: str) -> list[str]:
    """Lightweight segmenter for policy checks (jieba used in TextAnalyzer)."""
    import jieba

    return [w for w in jieba.lcut(text) if _HAN.fullmatch(w)]


def is_exempt(word: str, keywords: set[str]) -> bool:
    if word in keywords:
        return True
    # Latin capitals or Chinese place names ending in a toponym suffix.
    return bool(_PROPER.match(word))


def out_of_level_words(
    text: str,
    *,
    allowed: set[str],
    keywords: set[str],
) -> list[str]:
    bad: list[str] = []
    for w in chinese_words(text):
        if is_exempt(w, keywords):
            continue
        if w not in allowed and w not in bad:
            bad.append(w)
    return bad


def share_out_of_level(
    text: str,
    *,
    allowed: set[str],
    keywords: set[str],
) -> tuple[float, list[str]]:
    words = [w for w in chinese_words(text) if not is_exempt(w, keywords)]
    if not words:
        return 0.0, []
    bad = out_of_level_words(text, allowed=allowed, keywords=keywords)
    # Count unique violations against unique content words.
    unique = list(dict.fromkeys(words))
    share = len(bad) / max(1, len(unique))
    return share, bad


async def enforce_level_on_reply(
    generate: Callable[[list[str]], Awaitable[str]],
    *,
    first_reply: str,
    allowed: set[str],
    keywords: set[str],
    threshold: float,
) -> PostCheckResult:
    """Regenerate once if too many out-of-level words; then accept with marks.

    `generate` is an async callable(forbidden: list[str]) -> str.
    """
    share, bad = share_out_of_level(first_reply, allowed=allowed, keywords=keywords)
    if share <= threshold:
        return PostCheckResult(
            accepted=True,
            regenerated=False,
            out_of_level=tuple(bad),
            share=share,
            text=first_reply,
        )

    second = await generate(bad)
    share2, bad2 = share_out_of_level(second, allowed=allowed, keywords=keywords)
    return PostCheckResult(
        accepted=True,
        regenerated=True,
        out_of_level=tuple(bad2),
        share=share2,
        text=second,
    )


def vocab_size_is_monotonic() -> bool:
    prev = 0
    for level in range(1, 101):
        n = rules_for_level(level).vocab_size
        if n < prev:
            return False
        prev = n
    return True


def allowed_vocab_sample(words_by_rank: list[str], level: int, sample: int = 20) -> list[str]:
    n = rules_for_level(level).vocab_size
    cut = words_by_rank[:n]
    if len(cut) <= sample:
        return cut
    # Evenly spaced sample for the prompt hint.
    step = max(1, len(cut) // sample)
    return [cut[i] for i in range(0, len(cut), step)][:sample]
