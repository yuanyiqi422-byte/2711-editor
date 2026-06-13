"""Ban formulaic / beat-snippet garbage in choice labels."""

from __future__ import annotations

import re

from models import (
    _BOLD_FALLBACK_LABELS,
    _CAREFUL_FALLBACK_LABELS,
    derive_beat_choice_pair,
    enrich_node_choices,
    is_broken_choice_fragment,
    is_formulaic_choice_text,
)
from narrative_service import _skeleton_from_bible

_FORMULAIC = re.compile(r"徐徐图之|围绕.*图之")
_WATCH_SAY = re.compile(r"观望.*说|介入.*说")


def test_is_formulaic_choice_text_detects_banned_patterns() -> None:
    assert is_formulaic_choice_text("围绕「借项链」徐徐图之")
    assert is_formulaic_choice_text("徐徐图之")
    assert not is_formulaic_choice_text("追问项链下落")
    assert not is_formulaic_choice_text("沉默不语")


def test_is_broken_choice_fragment_detects_beat_snippet_garbage() -> None:
    assert is_broken_choice_fragment("先观望逾白说接近")
    assert is_broken_choice_fragment("立刻介入逾白说接近")
    assert is_broken_choice_fragment("观望逾白说接")
    assert not is_broken_choice_fragment("沉默观察")
    assert not is_broken_choice_fragment("当面追问")
    assert not is_broken_choice_fragment("追问项链下落")


def test_fallback_labels_are_standalone_verbs() -> None:
    for label in (*_CAREFUL_FALLBACK_LABELS, *_BOLD_FALLBACK_LABELS):
        assert "{" not in label
        assert not _FORMULAIC.search(label), label
        assert not _WATCH_SAY.search(label), label
        assert not is_broken_choice_fragment(label), label


def test_derive_beat_choice_pair_no_garbage_output() -> None:
    beat = "逾白说接近，气氛骤然紧张"
    title = "接近逾白"
    for variant in range(24):
        careful, bold = derive_beat_choice_pair(beat, title, variant=variant)
        for text in (careful, bold):
            assert not _FORMULAIC.search(text), text
            assert not _WATCH_SAY.search(text), text
            assert not is_broken_choice_fragment(text), text
            assert len(text) >= 4


def test_enrich_node_choices_no_garbage_output() -> None:
    choices = [
        {
            "id": "c1",
            "text": "三思后回应",
            "next": "a",
            "impact": "low",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
        {
            "id": "c2",
            "text": "果断抉择",
            "next": "b",
            "impact": "medium",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
    ]
    out = enrich_node_choices(
        choices,
        beat="逾白说接近",
        title="接近逾白",
        variant=0,
        avoid_signatures=set(),
    )
    for ch in out:
        text = str(ch.get("text") or "")
        assert not _FORMULAIC.search(text), text
        assert not _WATCH_SAY.search(text), text
        assert not is_broken_choice_fragment(text), text
        assert not is_formulaic_choice_text(text), text


def test_enrich_replaces_broken_llm_fragment() -> None:
    choices = [
        {
            "id": "c1",
            "text": "先观望逾白说接近",
            "next": "a",
            "impact": "low",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
        {
            "id": "c2",
            "text": "立刻介入逾白说接近",
            "next": "b",
            "impact": "medium",
            "immediate_consequence": "x",
            "narrative_impact": "y",
        },
    ]
    out = enrich_node_choices(
        choices,
        beat="逾白说接近",
        title="接近逾白",
        variant=0,
        avoid_signatures=set(),
    )
    for ch in out:
        text = str(ch.get("text") or "")
        assert not _WATCH_SAY.search(text), text
        assert not is_broken_choice_fragment(text), text


def test_skeleton_from_bible_choices_no_garbage_output() -> None:
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
    for raw in skeleton.values():
        if not isinstance(raw, dict):
            continue
        for ch in raw.get("choices") or []:
            if not isinstance(ch, dict):
                continue
            text = str(ch.get("text") or "")
            assert not _FORMULAIC.search(text), text
            assert not _WATCH_SAY.search(text), text
            assert not is_broken_choice_fragment(text), text
