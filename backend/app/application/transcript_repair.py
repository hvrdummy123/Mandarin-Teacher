"""Context-aware transcript repair (no LLM).

Browser STT often picks wrong Hanzi for similar sounds. When we know the topic
(e.g. family), bias toward topic keywords and a small set of common confusions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pypinyin import Style, lazy_pinyin

from app.domain.topics import Topic, get_topic

_HAN = re.compile(r"[\u4e00-\u9fff]+")

# (wrong, right) — applied when the topic makes `right` plausible.
_GLOBAL_FIXES: list[tuple[str, str]] = [
    ("借口有", "家有"),
    ("借口", "家"),  # only kept if topic bias includes 家 / 家人
    ("名词", "名字"),
    ("哪国人吗", "哪国人"),
]

# Topic id → extra wrong→right pairs
_TOPIC_FIXES: dict[str, list[tuple[str, str]]] = {
    "family": [
        ("借口有", "家有"),
        ("借口", "家"),
        ("我家借口", "我家"),
        ("几口人吗", "几口人"),
        ("三个人口", "三口人"),
        ("三人", "三口人"),  # only if 家 nearby — handled below
    ],
    "introduce": [
        ("名词", "名字"),
        ("我叫什么名字", "我叫"),  # STT echoing the question
    ],
    "restaurant": [
        ("买单吗", "买单"),
    ],
}


@dataclass(frozen=True)
class RepairResult:
    original: str
    text: str
    changed: bool
    note: str


def _py(text: str) -> str:
    return "".join(lazy_pinyin(text, style=Style.NORMAL))


def _topic_bias_words(topic: Topic | None) -> set[str]:
    if topic is None:
        return set()
    words = set(topic.keywords)
    for chunk in _HAN.findall(topic.opening_zh + topic.title_zh + topic.user_goal):
        if len(chunk) >= 2:
            words.add(chunk)
    # Always useful anchors for family talk
    if topic.id == "family":
        words.update({"家", "家人", "几口", "几口人", "爸爸", "妈妈", "哥哥", "姐姐"})
    if topic.id == "introduce":
        words.update({"名字", "叫", "学生", "哪里人"})
    return words


def repair_transcript(
    text: str,
    *,
    topic: Topic | None = None,
    topic_id: str | None = None,
) -> RepairResult:
    original = text.strip()
    if not original:
        return RepairResult(original=text, text=text, changed=False, note="")

    topic = topic or get_topic(topic_id)
    bias = _topic_bias_words(topic)
    out = original
    notes: list[str] = []

    fixes = list(_GLOBAL_FIXES)
    if topic is not None:
        fixes = list(_TOPIC_FIXES.get(topic.id, [])) + fixes

    for wrong, right in fixes:
        if wrong not in out:
            continue
        # Only apply "借口"→"家" style swaps when topic bias supports the fix.
        if right in bias or any(right in w or w in right for w in bias) or len(wrong) >= 3:
            if wrong == "借口" and "家" not in bias and topic and topic.id != "family":
                continue
            if wrong == "三人" and "家" not in out and "口" not in out:
                continue
            out = out.replace(wrong, right)
            notes.append(f"{wrong}→{right}")

    # Family-specific: …有三人 / …有三个人 → …有三口人 when talking about household
    if topic and topic.id == "family":
        replaced = re.sub(r"有三个人", "有三口人", out)
        replaced = re.sub(r"有三人", "有三口人", replaced)
        if replaced != out:
            notes.append("三人→三口人")
            out = replaced
        # 我+家 missing: 我有三口人 is ok; 我借口 already fixed

    # Replace a Hanzi span with a bias word if pinyin matches closely.
    if bias:
        for span in list(dict.fromkeys(_HAN.findall(out))):
            if span in bias or len(span) < 2:
                continue
            span_py = _py(span)
            for word in bias:
                if len(word) < 2:
                    continue
                w_py = _py(word)
                if span_py == w_py and span != word:
                    out = out.replace(span, word, 1)
                    notes.append(f"{span}→{word} (same pinyin)")
                    break
                # near-miss: jiakou vs jia — STT often inserts 借口 for 家
                if word == "家" and span_py in {"jieko", "jiekou", "jiakou"}:
                    out = out.replace(span, "家", 1)
                    notes.append(f"{span}→家")
                    break

    changed = out != original
    note = ""
    if changed:
        note = "Adjusted to fit this topic: " + ", ".join(notes[:4])
    return RepairResult(original=original, text=out, changed=changed, note=note)
