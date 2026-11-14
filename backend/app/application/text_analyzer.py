"""Deterministic Chinese segmentation + pinyin + dictionary enrichment."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import jieba
from pypinyin import Style, lazy_pinyin

from app.ports.dictionary import DictionaryRepo

_HAN_CHAR = re.compile(r"[\u4e00-\u9fff]")
_TOKEN_SPLIT = re.compile(r"([\u4e00-\u9fff]+|[a-zA-Z0-9]+|[^\s])")


@dataclass
class CharInfo:
    ch: str
    pinyin: str
    meaning: str


@dataclass
class Token:
    surface: str
    pinyin: str
    definitions: list[str]
    hsk: int | None
    chars: list[CharInfo]
    out_of_level: bool = False


def _tone_number(syllable: str) -> int:
    for ch in syllable:
        if ch in "āēīōūǖĀĒĪŌŪǕ":
            return 1
        if ch in "áéíóúǘÁÉÍÓÚǗ":
            return 2
        if ch in "ǎěǐǒǔǚǍĚǏǑǓǙ":
            return 3
        if ch in "àèìòùǜÀÈÌÒÙǛ":
            return 4
    return 5


def _tone_num(syllable: str) -> int:
    return _tone_number(syllable)


def _replace_tone_mark(syllable: str, new_tone: int) -> str:
    """Replace the tone mark on a syllable with new_tone (1–4) or strip to neutral."""
    # Map base vowel → tone variants.
    table = {
        "a": "āáǎàa",
        "e": "ēéěèe",
        "i": "īíǐìi",
        "o": "ōóǒòo",
        "u": "ūúǔùu",
        "ü": "ǖǘǚǜü",
        "v": "ǖǘǚǜü",
    }
    chars = list(syllable)
    for i, ch in enumerate(chars):
        lower = ch.lower()
        for base, tones in table.items():
            if lower in tones or lower == base:
                idx = new_tone - 1 if 1 <= new_tone <= 4 else 4
                repl = tones[idx]
                chars[i] = repl.upper() if ch.isupper() else repl
                return "".join(chars)
    return syllable


def _apply_bu_yi_sandhi(word: str, py_list: list[str]) -> list[str]:
    """Ensure 不/一 sandhi even when pypinyin leaves the citation tone.

    不 before tone 4 → bú; 一 before tone 4 → yí; 一 before 1/2/3 → yì.
    """
    if len(word) < 2 or len(py_list) < 2:
        return py_list
    out = list(py_list)
    if word[0] == "不":
        nxt = _tone_num(out[1])
        if nxt == 4:
            out[0] = _replace_tone_mark(out[0], 2)
    if word[0] == "一":
        nxt = _tone_num(out[1])
        if nxt == 4:
            out[0] = _replace_tone_mark(out[0], 2)
        elif nxt in {1, 2, 3}:
            out[0] = _replace_tone_mark(out[0], 4)
    return out


class TextAnalyzer:
    def __init__(self, dictionary: DictionaryRepo) -> None:
        self.dictionary = dictionary
        # Keep a few sandhi-sensitive compounds as single tokens.
        for w in ("不对", "一个", "一天", "银行", "重要", "你好"):
            jieba.add_word(w)

    def analyze(self, text: str, *, out_of_level: set[str] | None = None) -> list[Token]:
        out_of_level = out_of_level or set()
        tokens: list[Token] = []
        for piece in _TOKEN_SPLIT.findall(text):
            if not piece.strip():
                continue
            if _HAN_CHAR.search(piece):
                for word in jieba.lcut(piece):
                    tokens.append(self._word_token(word, out_of_level))
            else:
                tokens.append(
                    Token(
                        surface=piece,
                        pinyin="",
                        definitions=[],
                        hsk=None,
                        chars=[],
                        out_of_level=False,
                    )
                )
        return _sandhi_across_tokens(tokens)

    def _word_token(self, word: str, out_of_level: set[str]) -> Token:
        entries = self.dictionary.lookup(word)
        defs = entries[0].definitions[:3] if entries else []
        # Tone marks + sandhi; pass the whole jieba word so 银行/不对 get right readings.
        py_list = lazy_pinyin(word, style=Style.TONE, tone_sandhi=True, errors="default")
        py_list = _apply_bu_yi_sandhi(word, py_list)
        pinyin = " ".join(p for p in py_list if p)
        char_infos: list[CharInfo] = []
        for i, ch in enumerate(word):
            if not _HAN_CHAR.match(ch):
                continue
            ch_py = py_list[i] if i < len(py_list) else ""
            ch_entries = self.dictionary.lookup(ch)
            meaning = ch_entries[0].definitions[0] if ch_entries else ""
            char_infos.append(CharInfo(ch=ch, pinyin=ch_py, meaning=meaning))
        return Token(
            surface=word,
            pinyin=pinyin,
            definitions=defs,
            hsk=self.dictionary.hsk_level(word),
            chars=char_infos,
            out_of_level=word in out_of_level,
        )

    def tokens_as_dicts(
        self, text: str, *, out_of_level: set[str] | None = None
    ) -> list[dict[str, object]]:
        return [asdict(t) for t in self.analyze(text, out_of_level=out_of_level)]


def _sandhi_across_tokens(tokens: list[Token]) -> list[Token]:
    """Fix 不/一 when jieba split them from the following syllable."""
    out = list(tokens)
    for i, tok in enumerate(out[:-1]):
        nxt = out[i + 1]
        if not tok.pinyin or not nxt.pinyin:
            continue
        if tok.surface == "不":
            nxt_tone = _tone_number(nxt.pinyin.split()[0])
            if nxt_tone == 4:
                new_py = _replace_tone_mark(tok.pinyin.split()[0], 2)
                out[i] = Token(
                    surface=tok.surface,
                    pinyin=new_py,
                    definitions=tok.definitions,
                    hsk=tok.hsk,
                    chars=tok.chars,
                    out_of_level=tok.out_of_level,
                )
        if tok.surface == "一":
            nxt_tone = _tone_number(nxt.pinyin.split()[0])
            if nxt_tone == 4:
                new_py = _replace_tone_mark(tok.pinyin.split()[0], 2)
            elif nxt_tone in {1, 2, 3}:
                new_py = _replace_tone_mark(tok.pinyin.split()[0], 4)
            else:
                continue
            out[i] = Token(
                surface=tok.surface,
                pinyin=new_py,
                definitions=tok.definitions,
                hsk=tok.hsk,
                chars=tok.chars,
                out_of_level=tok.out_of_level,
            )
    return out
