"""In-memory dictionary for unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ports.dictionary import DictEntry


@dataclass
class MemoryDictionary:
    entries: dict[str, list[DictEntry]] = field(default_factory=dict)
    hsk: dict[str, int] = field(default_factory=dict)

    def lookup(self, word: str) -> list[DictEntry]:
        if word in self.entries:
            return self.entries[word]
        # traditional → simplified search
        for items in self.entries.values():
            for e in items:
                if e.traditional == word or e.simplified == word:
                    return [e]
        return []

    def hsk_level(self, word: str) -> int | None:
        return self.hsk.get(word)


def seed_basic_dictionary() -> MemoryDictionary:
    def e(simp: str, trad: str, py: str, *defs: str) -> DictEntry:
        return DictEntry(simplified=simp, traditional=trad, pinyin=py, definitions=list(defs))

    words = {
        "你好": [e("你好", "你好", "ni3 hao3", "hello; hi")],
        "你": [e("你", "你", "ni3", "you")],
        "好": [e("好", "好", "hao3", "good; well")],
        "银行": [e("银行", "銀行", "yin2 hang2", "bank")],
        "重要": [e("重要", "重要", "zhong4 yao4", "important")],
        "不": [e("不", "不", "bu4", "not")],
        "对": [e("对", "對", "dui4", "correct; right")],
        "不对": [e("不对", "不對", "bu2 dui4", "incorrect")],
        "一": [e("一", "一", "yi1", "one")],
        "个": [e("个", "個", "ge5", "measure word")],
        "天": [e("天", "天", "tian1", "day; sky")],
        "今天": [e("今天", "今天", "jin1 tian1", "today")],
        "怎么样": [e("怎么样", "怎麼樣", "zen3 me5 yang4", "how is it")],
        "我": [e("我", "我", "wo3", "I; me")],
        "是": [e("是", "是", "shi4", "to be")],
        "的": [e("的", "的", "de5", "possessive particle")],
        "吃": [e("吃", "吃", "chi1", "to eat")],
        "喝": [e("喝", "喝", "he1", "to drink")],
        "谢谢": [e("谢谢", "謝謝", "xie4 xie5", "thank you")],
        "中国": [e("中国", "中國", "zhong1 guo2", "China")],
        "人": [e("人", "人", "ren2", "person")],
    }
    hsk = {w: 1 for w in words}
    hsk["银行"] = 2
    hsk["重要"] = 3
    hsk["不对"] = 2
    return MemoryDictionary(entries=words, hsk=hsk)
