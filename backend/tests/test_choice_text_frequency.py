"""Game-wide choice text frequency cap (max 2 uses per label)."""

from __future__ import annotations

from collections import Counter

from graph_validate import (
    count_choice_nodes,
    validate_choice_text_frequency,
    validate_outline_structure,
)
from models import MAX_CHOICE_TEXT_USES, normalize_choice_text_key, rewrite_graph_choice_text_frequency
from narrative_service import _skeleton_from_bible


def _choice_text_counts(skeleton: dict) -> Counter[str]:
    counts: Counter[str] = Counter()
    for raw in skeleton.values():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        for ch in raw.get("choices") or []:
            if not isinstance(ch, dict):
                continue
            key = normalize_choice_text_key(str(ch.get("text") or ""))
            if key:
                counts[key] += 1
    return counts


def test_ten_node_skeleton_no_choice_text_over_two_uses() -> None:
    bible = {
        "plot_beats": [
            "开端",
            "冲突甲",
            "冲突乙",
            "冲突丙",
            "高潮前夜",
            "高潮",
            "转折",
            "收束",
        ],
        "endings": [
            {"id": "e1", "label": "携手走向黎明"},
            {"id": "e2", "label": "天涯各一方"},
            {"id": "e3", "label": "平淡如常"},
        ],
    }
    skeleton, start_id = _skeleton_from_bible(bible, 20_000)

    non_ending = sum(
        1 for raw in skeleton.values() if isinstance(raw, dict) and not raw.get("is_ending")
    )
    assert 8 <= non_ending <= 12

    counts = _choice_text_counts(skeleton)
    for key, count in counts.items():
        assert count <= MAX_CHOICE_TEXT_USES, f"「{key}」出现 {count} 次"

    assert not validate_choice_text_frequency(skeleton)

    scale_min_choices = 4
    assert count_choice_nodes(skeleton) >= scale_min_choices

    ratio_errors = [
        e
        for e in validate_outline_structure(
            skeleton,
            start_id,
            min_choice_nodes=scale_min_choices,
            relaxed=True,
        )
        if "抉择点占比" in e or "抉择点仅" in e
    ]
    assert not ratio_errors


def test_validate_choice_text_frequency_detects_triplicate() -> None:
    nodes = {
        "start": {
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "a", "impact": "low"},
                {"id": "c2", "text": "转身离开", "next": "b", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "a": {
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "点头答应", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "b": {
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "摇头拒绝", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "e1": {"is_ending": True, "ending_type": "good", "choices": []},
        "e2": {"is_ending": True, "ending_type": "bad", "choices": []},
    }
    errors = validate_choice_text_frequency(nodes)
    assert errors
    assert "当面追问" in errors[0]
    assert "3" in errors[0]


def test_rewrite_graph_choice_text_frequency_fixes_triplicate() -> None:
    nodes = {
        "start": {
            "title": "开端",
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "a", "impact": "low"},
                {"id": "c2", "text": "转身离开", "next": "b", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "a": {
            "title": "冲突",
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "点头答应", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "b": {
            "title": "高潮",
            "choices": [
                {"id": "c1", "text": "当面追问", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "摇头拒绝", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "e1": {"is_ending": True, "ending_type": "good", "choices": []},
        "e2": {"is_ending": True, "ending_type": "bad", "choices": []},
    }
    rewrite_graph_choice_text_frequency(nodes, node_order=["start", "a", "b", "e1", "e2"])
    assert not validate_choice_text_frequency(nodes)
    counts = _choice_text_counts(nodes)
    assert counts[normalize_choice_text_key("当面追问")] == 2
