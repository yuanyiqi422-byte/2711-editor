"""Ban formulaic choice phrasing like 徐徐图之 / 围绕…图之."""

from __future__ import annotations

import re

from models import (
    _BOLD_BEAT_TEMPLATES,
    _CAREFUL_BEAT_TEMPLATES,
    derive_beat_choice_pair,
    enrich_node_choices,
    is_formulaic_choice_text,
)
from narrative_service import _skeleton_from_bible

_FORMULAIC = re.compile(r"徐徐图之|围绕.*图之")


def test_is_formulaic_choice_text_detects_banned_patterns() -> None:
    assert is_formulaic_choice_text("围绕「借项链」徐徐图之")
    assert is_formulaic_choice_text("徐徐图之")
    assert not is_formulaic_choice_text("追问项链下落")
    assert not is_formulaic_choice_text("沉默不语")


def test_beat_templates_contain_no_formulaic_phrasing() -> None:
    for tpl in (*_CAREFUL_BEAT_TEMPLATES, *_BOLD_BEAT_TEMPLATES):
        sample = tpl.format(snip="测试")
        assert not _FORMULAIC.search(sample), f"template leaked: {sample}"


def test_derive_beat_choice_pair_no_formulaic_output() -> None:
    for variant in range(24):
        careful, bold = derive_beat_choice_pair(
            "借项链赴晚会",
            "晚会抉择",
            variant=variant,
        )
        assert not _FORMULAIC.search(careful), careful
        assert not _FORMULAIC.search(bold), bold


def test_enrich_node_choices_no_formulaic_output() -> None:
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
        beat="遗失项链",
        title="项链失踪",
        variant=0,
        avoid_signatures=set(),
    )
    for ch in out:
        text = str(ch.get("text") or "")
        assert not _FORMULAIC.search(text), text
        assert not is_formulaic_choice_text(text), text


def test_skeleton_from_bible_choices_no_formulaic_output() -> None:
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
