"""Speed opts must not undercut narrative quality floors."""

from __future__ import annotations

from graph_validate import count_choice_nodes, validate_outline_structure
from narrative_service import (
    _merge_node_preserved_fields,
    _should_skip_outline_llm,
    _skeleton_from_bible,
    _validate_fast_path_skeleton,
)
from prompts import narrative_quality_floor, narrative_scale


def test_quality_floor_20k_nodes_endings_choices() -> None:
    floor = narrative_quality_floor(20_000)
    assert floor["nodes_min"] >= 14
    assert floor["endings_min"] == 3
    assert floor["min_choice_moments"] >= 5

    scale = narrative_scale(20_000)
    assert scale["nodes_min"] >= 14
    assert scale["endings_min"] == 3
    assert scale["min_choice_moments"] >= 5


def test_fast_path_skeleton_passes_validate_at_20k() -> None:
    bible = {"plot_beats": [f"节拍{i}" for i in range(12)]}
    skeleton, start_id = _skeleton_from_bible(bible, 20_000)
    scale = narrative_scale(20_000)

    assert len(skeleton) >= scale["nodes_min"]
    assert count_choice_nodes(skeleton) >= int(scale["min_choice_moments"])

    errors = _validate_fast_path_skeleton(skeleton, start_id, 20_000)
    assert errors == [], errors


def test_fast_path_skeleton_passes_strict_endings_and_choices() -> None:
    """Relaxed 放宽占比；结局数与抉择下限仍须满足。"""
    bible = {"plot_beats": [f"节拍{i}" for i in range(10)]}
    skeleton, start_id = _skeleton_from_bible(bible, 8000)
    scale = narrative_scale(8000)

    errors = validate_outline_structure(
        skeleton,
        start_id,
        min_endings=int(scale["endings_min"]),
        min_choice_nodes=int(scale["min_choice_moments"]),
        relaxed=True,
    )
    critical = [
        e
        for e in errors
        if "结局节点仅" in e or "抉择点仅" in e or "不可达" in e or "死路" in e
    ]
    assert critical == [], critical


def test_narrative_speed_mode_fast_skips_outline_only(monkeypatch) -> None:
    monkeypatch.setenv("NARRATIVE_SPEED_MODE", "fast")
    import narrative_service as ns

    monkeypatch.setattr(ns, "NARRATIVE_SPEED_MODE", "fast")
    bible = {"plot_beats": ["a"]}
    assert _should_skip_outline_llm(50_000, bible) is True


def test_skeleton_from_bible_choice_ratio_at_2k() -> None:
    """Short-text fast-path skeleton must meet graph_validate choice density."""
    bible = {"plot_beats": [f"节拍{i}" for i in range(6)]}
    skeleton, start_id = _skeleton_from_bible(bible, 2000)
    scale = narrative_scale(2000)

    assert len(skeleton) >= int(scale["nodes_min"])
    choice_nodes = count_choice_nodes(skeleton)
    assert choice_nodes >= int(scale["min_choice_moments"])

    non_ending = sum(
        1 for n in skeleton.values() if isinstance(n, dict) and not n.get("is_ending")
    )
    assert choice_nodes / non_ending >= 0.35

    errors = validate_outline_structure(
        skeleton,
        start_id,
        min_endings=int(scale["endings_min"]),
        min_choice_nodes=int(scale["min_choice_moments"]) if len(skeleton) >= 8 else 0,
    )
    assert not any("抉择点占比" in e for e in errors), errors


def test_finalize_scene_nodes_restores_skeleton_choices() -> None:
    from models import StoryNode
    from narrative_service import _finalize_scene_nodes, _skeleton_from_bible

    bible = {"plot_beats": [f"节拍{i}" for i in range(6)]}
    skeleton, _ = _skeleton_from_bible(bible, 2000)
    merged = {
        nid: StoryNode.model_validate(
            {
                "id": nid,
                "title": nid,
                "lines": [{"speaker": "旁白", "text": "对白"}],
                "choices": [],
                "after_lines_next": raw.get("after_lines_next") or "",
                "is_ending": bool(raw.get("is_ending")),
            }
        )
        for nid, raw in skeleton.items()
        if isinstance(raw, dict)
    }
    finalized = _finalize_scene_nodes(merged, skeleton)
    choice_nodes = count_choice_nodes(
        {nid: n.model_dump() for nid, n in finalized.items()}
    )
    assert choice_nodes >= 3


def test_merge_node_preserves_skeleton_choices_when_batch_empty() -> None:
    skel_choices = [
        {
            "id": "c1",
            "text": "A",
            "next": "scene_2",
            "impact": "medium",
            "immediate_consequence": "a",
            "narrative_impact": "a",
        },
        {
            "id": "c2",
            "text": "B",
            "next": "scene_3",
            "impact": "low",
            "immediate_consequence": "b",
            "narrative_impact": "b",
        },
    ]
    skeleton = {
        "id": "scene_1",
        "choices": skel_choices,
        "after_lines_next": "",
        "is_ending": False,
    }
    batch = {
        "id": "scene_1",
        "title": "场景",
        "lines": [{"speaker": "旁白", "text": "对白"}],
        "choices": [],
    }
    merged = _merge_node_preserved_fields(skeleton, batch)
    assert len(merged["choices"]) == 2
    assert [c["text"] for c in merged["choices"]] == ["A", "B"]
    assert [c["next"] for c in merged["choices"]] == ["scene_2", "scene_3"]


def test_merge_node_ignores_batch_is_ending_when_skeleton_linear() -> None:
    skeleton = {
        "id": "scene_2",
        "choices": [
            {
                "id": "c1",
                "text": "A",
                "next": "scene_3",
                "impact": "medium",
                "immediate_consequence": "a",
                "narrative_impact": "a",
            },
            {
                "id": "c2",
                "text": "B",
                "next": "scene_4",
                "impact": "low",
                "immediate_consequence": "b",
                "narrative_impact": "b",
            },
        ],
        "after_lines_next": "",
        "is_ending": False,
    }
    batch = {
        "id": "scene_2",
        "title": "场景",
        "lines": [{"speaker": "旁白", "text": "对白"}],
        "choices": [],
        "is_ending": True,
        "ending_type": "neutral",
    }
    merged = _merge_node_preserved_fields(skeleton, batch)
    assert merged["is_ending"] is False
    assert len(merged["choices"]) == 2


def test_merge_node_keeps_batch_choices_when_llm_returns_full_set() -> None:
    skel_choices = [
        {"id": "c1", "text": "骨架A", "next": "a", "impact": "low"},
        {"id": "c2", "text": "骨架B", "next": "b", "impact": "low"},
    ]
    batch_choices = [
        {
            "id": "c1",
            "text": "LLM A",
            "next": "a",
            "impact": "high",
            "immediate_consequence": "x",
            "narrative_impact": "x",
        },
        {
            "id": "c2",
            "text": "LLM B",
            "next": "b",
            "impact": "medium",
            "immediate_consequence": "y",
            "narrative_impact": "y",
        },
    ]
    merged = _merge_node_preserved_fields(
        {"choices": skel_choices, "after_lines_next": ""},
        {"choices": batch_choices, "lines": [{"speaker": "旁白", "text": "x"}]},
    )
    assert [c["text"] for c in merged["choices"]] == ["LLM A", "LLM B"]
    assert [c["impact"] for c in merged["choices"]] == ["high", "medium"]
