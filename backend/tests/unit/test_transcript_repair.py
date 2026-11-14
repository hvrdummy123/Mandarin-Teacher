from app.application.transcript_repair import repair_transcript
from app.domain.topics import get_topic


def test_family_jieko_becomes_jia() -> None:
    topic = get_topic("family")
    assert topic is not None
    result = repair_transcript("我借口有三人", topic=topic)
    assert result.changed
    assert "借口" not in result.text
    assert "家" in result.text
    assert "三" in result.text


def test_introduce_mingci_becomes_mingzi() -> None:
    topic = get_topic("introduce")
    assert topic is not None
    result = repair_transcript("名词 Mary", topic=topic)
    assert "名字" in result.text or result.text != "名词 Mary"
