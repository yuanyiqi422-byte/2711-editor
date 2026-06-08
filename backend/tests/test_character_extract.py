"""主角名启发式提取单元测试。"""

from __future__ import annotations

from character_extract import (
    extract_protagonist_candidates,
    extract_protagonist_candidates_enhanced,
)

_FALSE_POSITIVE_SAMPLE = """
林婉儿站在崖边，望着云海出神。这儿风很大，吹得她衣袂猎猎作响。
师兄轻轻走到她身后，低声道：「不逼你了，你自己想清楚。」
林婉儿回头，对师兄说：「我知道。」
这里不是名字，那里也不是。他她它我们你们都不该出现。
"""

_INTRO_SAMPLE = """
第一章 初入宗门

主角名叫苏清歌，乃是青云宗外门弟子。
苏清歌的剑法尚浅，却在晨雾中独自练剑。
"""

_POV_SAMPLE = """
我叫陈默，在这个世界已经待了三年。
陈默走在雨巷里，心想这一切何时才能结束。
"""

_DIALOGUE_TRAP = """
「这儿风很大。」他望着窗外说。
师兄道：「不逼你了。」
李青云抬头：「我知道。」
李青云的剑在鞘中轻鸣。李青云转身离去。
"""


def _names(chars: list[dict]) -> list[str]:
    return [c["name"] for c in chars]


def test_filters_demonstratives_titles_and_phrase_fragments() -> None:
    chars = extract_protagonist_candidates(_FALSE_POSITIVE_SAMPLE)
    names = _names(chars)
    assert "这儿" not in names
    assert "这里" not in names
    assert "那里" not in names
    assert "师兄" not in names
    assert "不逼你" not in names
    assert "风很" not in names
    assert "他" not in names
    assert "我们" not in names


def test_prefers_real_protagonist_name() -> None:
    chars = extract_protagonist_candidates(_FALSE_POSITIVE_SAMPLE)
    names = _names(chars)
    assert names, "应识别到真实人名"
    assert names[0] == "林婉儿"


def test_intro_pattern() -> None:
    chars = extract_protagonist_candidates(_INTRO_SAMPLE)
    assert _names(chars)[0] == "苏清歌"


def test_pov_pattern() -> None:
    chars = extract_protagonist_candidates(_POV_SAMPLE)
    assert _names(chars)[0] == "陈默"


def test_dialogue_trap_prefers_surname_name() -> None:
    chars = extract_protagonist_candidates(_DIALOGUE_TRAP)
    names = _names(chars)
    assert "这儿" not in names
    assert "师兄" not in names
    assert "不逼你" not in names
    assert names and names[0] == "李青云"


def test_low_confidence_returns_empty_not_garbage() -> None:
    garbage = "这儿风很大。那里没有人。师兄师姐师父都在。不逼你了。怎么这样。"
    chars = extract_protagonist_candidates(garbage)
    assert chars == []


def test_candidates_include_confidence() -> None:
    chars = extract_protagonist_candidates(_INTRO_SAMPLE)
    assert chars
    assert "confidence" in chars[0]
    assert chars[0]["confidence"] >= 55


async def test_enhanced_returns_low_confidence_flag() -> None:
    result = await extract_protagonist_candidates_enhanced(
        "这儿风很大。师兄说：不逼你了。"
    )
    assert "low_confidence" in result
    assert "characters" in result
    assert result["low_confidence"] is True
