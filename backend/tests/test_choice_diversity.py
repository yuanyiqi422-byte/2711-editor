"""Choice text diversity across stories and nodes."""

from __future__ import annotations

from graph_validate import validate_choice_text_diversity
from models import choice_text_set_signature, is_generic_choice_text
from narrative_service import _enrich_pack_choices, _skeleton_from_bible


def _mid_choice_signatures(skeleton: dict) -> list[tuple[str, ...]]:
    sigs: list[tuple[str, ...]] = []
    for raw in skeleton.values():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if len(choices) < 2:
            continue
        if any(
            isinstance(ch, dict) and str(ch.get("next") or "").startswith("ending_")
            for ch in choices
        ):
            continue
        sig = choice_text_set_signature(choices)
        if len(sig) >= 2:
            sigs.append(sig)
    return sigs


def test_two_bibles_produce_different_choice_texts() -> None:
    bible_campus = {
        "plot_beats": [
            "开学暗恋同桌",
            "借笔记靠近",
            "操场告白",
            "误会冷战",
            "图书馆和解",
            "毕业典礼",
        ],
        "endings": [
            {"id": "e1", "label": "牵手走出校门"},
            {"id": "e2", "label": "各自奔赴前程"},
            {"id": "e3", "label": "保持朋友距离"},
        ],
    }
    bible_xianxia = {
        "plot_beats": [
            "拜入仙门",
            "丹田受损",
            "秘境夺药",
            "师门问责",
            "渡劫重生",
            "飞升抉择",
        ],
        "endings": [
            {"id": "e1", "label": "飞升仙界"},
            {"id": "e2", "label": "堕魔离去"},
            {"id": "e3", "label": "隐世修行"},
        ],
    }
    sk_campus, _ = _skeleton_from_bible(bible_campus, 5000)
    sk_xianxia, _ = _skeleton_from_bible(bible_xianxia, 5000)

    campus_sigs = _mid_choice_signatures(sk_campus)
    xianxia_sigs = _mid_choice_signatures(sk_xianxia)
    assert campus_sigs
    assert xianxia_sigs
    assert campus_sigs != xianxia_sigs

    assert set(campus_sigs).isdisjoint(set(xianxia_sigs))


def test_skeleton_choice_nodes_not_generic_templates() -> None:
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
            assert not is_generic_choice_text(text), f"generic label leaked: {text}"


def test_consecutive_choice_nodes_do_not_repeat_signatures() -> None:
    bible = {
        "plot_beats": ["开端", "冲突甲", "冲突乙", "冲突丙", "高潮", "收束"],
    }
    skeleton, _ = _skeleton_from_bible(bible, 8000)
    sigs = _mid_choice_signatures(skeleton)
    assert len(sigs) == len(set(sigs))


def test_validate_choice_text_diversity_rejects_identical_sets() -> None:
    nodes = {
        "start": {
            "choices": [
                {"id": "c1", "text": "三思后回应", "next": "a", "impact": "low"},
                {"id": "c2", "text": "果断抉择", "next": "b", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "a": {
            "choices": [
                {"id": "c1", "text": "三思后回应", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "果断抉择", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "b": {
            "choices": [
                {"id": "c1", "text": "三思后回应", "next": "e1", "impact": "low"},
                {"id": "c2", "text": "果断抉择", "next": "e2", "impact": "medium"},
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "e1": {"is_ending": True, "ending_type": "good", "choices": []},
        "e2": {"is_ending": True, "ending_type": "bad", "choices": []},
    }
    errors = validate_choice_text_diversity(nodes)
    assert errors
    assert "50%" in errors[0] or "相同" in errors[0]
