"""主角名启发式提取单元测试。"""

from __future__ import annotations

import asyncio

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

TOLSTOY = (
    "列夫·托尔斯泰是俄国最伟大的作家之一。他下个礼拜要在莫斯科会见朋友。"
    "渥伦斯基在车站遇见了安娜。伦斯基对这一切感到困惑。"
)

_TOLSTOY_TRAP = TOLSTOY

_TOLSTOY_CLASSIC = """
列夫·托尔斯泰是俄国最伟大的作家之一。
渥伦斯基在车站遇见了安娜·卡列尼娜。
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


def test_tolstoy_fragment_trap() -> None:
    for sample in (_TOLSTOY_TRAP, _TOLSTOY_CLASSIC):
        chars = extract_protagonist_candidates(sample)
        names = _names(chars)
        assert "他下个礼" not in names
        assert "尔斯泰" not in names
        assert "伦斯基" not in names


def test_surnames_is_char_level_frozenset() -> None:
    from character_extract import _SURNAMES

    assert isinstance(_SURNAMES, frozenset)
    assert all(len(ch) == 1 for ch in _SURNAMES)
    assert "李" in _SURNAMES
    assert "李王" not in _SURNAMES


def test_tolstoy_full_names_not_suffix_fragments() -> None:
    from character_extract import _is_bad_token_slice, _is_plausible_name

    text = TOLSTOY
    for bad in ("尔斯泰", "伦斯基", "他下个礼"):
        assert _is_bad_token_slice(bad, text)
        assert not _is_plausible_name(bad, text=text)


def test_enhanced_returns_low_confidence_flag() -> None:
    result = asyncio.run(
        extract_protagonist_candidates_enhanced("这儿风很大。师兄说：不逼你了。")
    )
    assert "low_confidence" in result
    assert "characters" in result
    assert result["low_confidence"] is True


def test_known_bad_name_slices_blocklist() -> None:
    from character_extract import _is_plausible_name

    assert not _is_plausible_name("伦斯基", text="伦斯基对这一切感到困惑。")
    assert not _is_plausible_name("尔斯泰", text="列夫·托尔斯泰是伟大的作家。")

