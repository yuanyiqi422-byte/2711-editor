"""Choice display text sanitization and per-node distinctness."""

from models import (
    ensure_distinct_choice_texts,
    normalize_choice_text_key,
    prepare_choice_dicts,
    sanitize_choice_display_text,
)
from narrative_service import _merge_node_preserved_fields, _skeleton_from_bible


def test_sanitize_choice_display_text_strips_trailing_parenthetical():
    raw = "三思后回应（晚会上玛蒂尔德大获成功，）"
    assert sanitize_choice_display_text(raw) == "三思后回应"
    assert sanitize_choice_display_text("果断抉择（晚会上玛蒂尔德大获成功，）") == "果断抉择"
    assert sanitize_choice_display_text("当面质问(对方转身离开)") == "当面质问"


def test_sanitize_choice_display_text_keeps_action_only_label():
    assert sanitize_choice_display_text("暂且观望") == "暂且观望"
    assert sanitize_choice_display_text("  主动出击  ") == "主动出击"


def test_ensure_distinct_choice_texts_dedupes_after_normalize():
    choices = [
        {
            "id": "c1",
            "text": "三思后回应（晚会上玛蒂尔德大获成功，）",
            "next": "a",
            "impact": "low",
            "immediate_consequence": "气氛缓和",
            "narrative_impact": "微调关系",
        },
        {
            "id": "c2",
            "text": "三思后回应（晚会上玛蒂尔德大获成功，）",
            "next": "b",
            "impact": "medium",
            "immediate_consequence": "跳过铺垫",
            "narrative_impact": "改变节奏",
        },
    ]
    out = ensure_distinct_choice_texts(choices)
    keys = [normalize_choice_text_key(c["text"]) for c in out]
    assert len(keys) == 2
    assert len(set(keys)) == 2
    assert out[0]["text"] == "三思后回应"


def test_prepare_choice_dicts_sanitizes_maupassant_style_leak():
    raw = [
        {
            "id": "c1",
            "text": "三思后回应（晚会上玛蒂尔德大获成功，）",
            "next": "scene_2",
            "impact": "low",
            "immediate_consequence": "气氛缓和，按原节拍推进",
            "narrative_impact": "微调人物关系",
        },
        {
            "id": "c2",
            "text": "果断抉择（晚会上玛蒂尔德大获成功，）",
            "next": "scene_3",
            "impact": "medium",
            "immediate_consequence": "跳过铺垫，直接进入下一冲突",
            "narrative_impact": "改变后续场景节奏",
        },
    ]
    out = prepare_choice_dicts(raw)
    assert out[0]["text"] == "三思后回应"
    assert out[1]["text"] == "果断抉择"
    assert out[0]["immediate_consequence"] == "气氛缓和，按原节拍推进"


def test_merge_node_sanitizes_skeleton_choices():
    skeleton = {
        "id": "scene_2",
        "choices": [
            {
                "id": "c1",
                "text": "三思后回应（晚会上玛蒂尔德大获成功，）",
                "next": "scene_3",
                "impact": "low",
                "immediate_consequence": "a",
                "narrative_impact": "a",
            },
            {
                "id": "c2",
                "text": "果断抉择（晚会上玛蒂尔德大获成功，）",
                "next": "scene_4",
                "impact": "medium",
                "immediate_consequence": "b",
                "narrative_impact": "b",
            },
        ],
        "after_lines_next": "",
        "is_ending": False,
    }
    merged = _merge_node_preserved_fields(
        skeleton,
        {"lines": [{"speaker": "旁白", "text": "对白"}], "choices": []},
    )
    texts = [c["text"] for c in merged["choices"]]
    assert len(texts) == 2
    assert len(set(texts)) == 2
    for t in texts:
        assert "（" not in t and "(" not in t
        assert "玛蒂尔德" not in t


def test_skeleton_from_bible_choice_labels_distinct_per_node():
    bible = {
        "plot_beats": [
            "玛蒂尔德向往上流",
            "借项链赴晚会",
            "晚会上玛蒂尔德大获成功",
            "遗失项链",
            "十年还债",
            "真相揭晓",
        ],
    }
    skeleton, _ = _skeleton_from_bible(bible, 5000)
    choice_nodes = [
        nid
        for nid, raw in skeleton.items()
        if isinstance(raw, dict) and len(raw.get("choices") or []) >= 2
    ]
    assert choice_nodes
    for nid in choice_nodes:
        texts = [c["text"] for c in skeleton[nid]["choices"]]
        assert len(texts) == len(set(texts))
        for t in texts:
            assert "（" not in t and "(" not in t
