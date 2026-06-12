"""enrich_node_choices must not overwrite already-specific LLM choice labels."""

from __future__ import annotations

from models import enrich_node_choices, is_generic_choice_text


def test_enrich_preserves_specific_llm_choice_text() -> None:
    choices = [
        {
            "id": "c1",
            "text": "追问项链下落",
            "next": "a",
            "impact": "medium",
            "immediate_consequence": "对方神色慌张",
            "narrative_impact": "锁定关键线索",
        },
        {
            "id": "c2",
            "text": "沉默不语",
            "next": "b",
            "impact": "low",
            "immediate_consequence": "气氛凝滞",
            "narrative_impact": "关系微妙变化",
        },
    ]
    out = enrich_node_choices(
        choices,
        beat="遗失项链",
        title="项链失踪",
        variant=0,
        avoid_signatures=set(),
    )
    assert out[0]["text"] == "追问项链下落"
    assert out[1]["text"] == "沉默不语"
    assert not is_generic_choice_text(out[0]["text"])
    assert not is_generic_choice_text(out[1]["text"])


def test_enrich_only_replaces_generic_slots() -> None:
    choices = [
        {
            "id": "c1",
            "text": "当面揭穿真相",
            "next": "a",
            "impact": "high",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
        {
            "id": "c2",
            "text": "三思后回应",
            "next": "b",
            "impact": "low",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
    ]
    out = enrich_node_choices(
        choices,
        beat="真相揭晓",
        title="最后对质",
        variant=0,
        avoid_signatures=set(),
    )
    assert out[0]["text"] == "当面揭穿真相"
    assert out[1]["text"] != "三思后回应"
    assert not is_generic_choice_text(out[1]["text"])
