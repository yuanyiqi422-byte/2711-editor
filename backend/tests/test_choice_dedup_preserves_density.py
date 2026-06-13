"""Choice dedup must rewrite labels only — never drop nodes or choice moments."""

from __future__ import annotations

import copy
from unittest.mock import patch

from graph_validate import count_choice_nodes, validate_choice_text_frequency
from models import MAX_CHOICE_TEXT_USES, normalize_choice_text_key, rewrite_graph_choice_text_frequency
from narrative_service import _enrich_skeleton_choices, _skeleton_from_bible


def _choice_node_ids(skeleton: dict) -> set[str]:
    return {
        nid
        for nid, raw in skeleton.items()
        if isinstance(raw, dict) and len(raw.get("choices") or []) >= 2
    }


def test_skeleton_keeps_all_bible_plot_beats() -> None:
    beats = [f"关键节拍{i}" for i in range(12)]
    bible = {"plot_beats": beats}
    skeleton, _ = _skeleton_from_bible(bible, 5000)
    scene_nodes = [
        nid
        for nid, raw in skeleton.items()
        if isinstance(raw, dict) and not raw.get("is_ending")
    ]
    assert len(scene_nodes) >= len(beats)


def test_enrich_preserves_node_and_choice_counts() -> None:
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
    with patch("narrative_service._enrich_skeleton_choices"):
        skeleton, _ = _skeleton_from_bible(bible, 20_000)

    node_count_before = len(skeleton)
    choice_nodes_before = _choice_node_ids(skeleton)
    choice_count_before = len(choice_nodes_before)

    _enrich_skeleton_choices(skeleton, bible)

    assert len(skeleton) == node_count_before
    assert len(_choice_node_ids(skeleton)) == choice_count_before
    assert _choice_node_ids(skeleton) == choice_nodes_before
    assert not validate_choice_text_frequency(skeleton)
    for key, count in _choice_text_counts(skeleton).items():
        assert count <= MAX_CHOICE_TEXT_USES, f"「{key}」出现 {count} 次"


def test_rewrite_graph_preserves_node_and_choice_counts() -> None:
    bible = {
        "plot_beats": ["开端", "冲突", "高潮", "收束"],
        "endings": [
            {"id": "e1", "label": "花好月圆"},
            {"id": "e2", "label": "各奔东西"},
            {"id": "e3", "label": "平淡收场"},
        ],
    }
    skeleton, _ = _skeleton_from_bible(bible, 8000)
    before_nodes = set(skeleton.keys())
    before_choices = _choice_node_ids(skeleton)

    raw = copy.deepcopy(skeleton)
    rewrite_graph_choice_text_frequency(raw, node_order=list(skeleton.keys()))

    assert set(raw.keys()) == before_nodes
    assert _choice_node_ids(raw) == before_choices
    assert not validate_choice_text_frequency(raw)


def _choice_text_counts(skeleton: dict):
    from collections import Counter

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
