"""graph_validate unit tests."""

from __future__ import annotations

from graph_validate import (
    count_choice_nodes,
    outline_soft_pass,
    validate_outline_structure,
)


def _three_ending_outline() -> dict[str, dict]:
    return {
        "start": {
            "id": "start",
            "after_lines_next": "choice",
            "choices": [],
            "is_ending": False,
        },
        "choice": {
            "id": "choice",
            "choices": [
                {
                    "id": "c1",
                    "text": "A",
                    "next": "good",
                    "impact": "high",
                    "immediate_consequence": "帮助",
                    "narrative_impact": "good_end",
                },
                {
                    "id": "c2",
                    "text": "B",
                    "next": "bad",
                    "impact": "high",
                    "immediate_consequence": "离开",
                    "narrative_impact": "bad_end",
                },
                {
                    "id": "c3",
                    "text": "C",
                    "next": "neutral",
                    "impact": "medium",
                    "immediate_consequence": "妥协",
                    "narrative_impact": "neutral_end",
                },
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "good": {"id": "good", "is_ending": True, "ending_type": "good", "choices": []},
        "bad": {"id": "bad", "is_ending": True, "ending_type": "bad", "choices": []},
        "neutral": {
            "id": "neutral",
            "is_ending": True,
            "ending_type": "neutral",
            "choices": [],
        },
    }


def _branchy_outline(node_count: int = 12) -> dict[str, dict]:
    """含足够抉择点占比的骨架，用于密度校验。"""
    nodes: dict[str, dict] = {
        "start": {
            "id": "start",
            "after_lines_next": "s2",
            "choices": [],
            "is_ending": False,
        },
    }
    for i in range(2, node_count - 2):
        nid = f"s{i}"
        if i % 2 == 0:
            nodes[nid] = {
                "id": nid,
                "after_lines_next": "",
                "choices": [
                    {
                        "id": f"c{i}a",
                        "text": f"选 {i}A",
                        "next": f"s{i + 1}",
                        "impact": "high" if i % 4 == 0 else "medium",
                        "immediate_consequence": f"后果 {i}a",
                        "narrative_impact": f"影响 {i}a",
                    },
                    {
                        "id": f"c{i}b",
                        "text": f"选 {i}B",
                        "next": f"s{i + 1}",
                        "impact": "low",
                        "immediate_consequence": f"后果 {i}b",
                        "narrative_impact": f"影响 {i}b",
                    },
                ],
                "is_ending": False,
            }
        else:
            nodes[nid] = {
                "id": nid,
                "after_lines_next": f"s{i + 1}",
                "choices": [],
                "is_ending": False,
            }
    penult = node_count - 2
    nodes[f"s{penult}"] = {
        "id": f"s{penult}",
        "after_lines_next": "",
        "choices": [
            {
                "id": "c_good",
                "text": "好",
                "next": "good",
                "impact": "high",
                "immediate_consequence": "好结局",
                "narrative_impact": "good",
            },
            {
                "id": "c_bad",
                "text": "坏",
                "next": "bad",
                "impact": "high",
                "immediate_consequence": "坏结局",
                "narrative_impact": "bad",
            },
            {
                "id": "c_neutral",
                "text": "平",
                "next": "neutral",
                "impact": "medium",
                "immediate_consequence": "中性结局",
                "narrative_impact": "neutral",
            },
        ],
        "is_ending": False,
    }
    nodes["good"] = {"id": "good", "is_ending": True, "ending_type": "good", "choices": []}
    nodes["bad"] = {"id": "bad", "is_ending": True, "ending_type": "bad", "choices": []}
    nodes["neutral"] = {
        "id": "neutral",
        "is_ending": True,
        "ending_type": "neutral",
        "choices": [],
    }
    nodes[f"s{penult - 1}"]["after_lines_next"] = f"s{penult}"
    return nodes


def test_valid_minimal_outline() -> None:
    nodes = _three_ending_outline()
    errors = validate_outline_structure(nodes, "start")
    assert errors == []


def test_rejects_fewer_than_three_endings() -> None:
    nodes = {
        "start": {
            "id": "start",
            "after_lines_next": "choice",
            "choices": [],
            "is_ending": False,
        },
        "choice": {
            "id": "choice",
            "choices": [
                {
                    "id": "c1",
                    "text": "A",
                    "next": "good",
                    "impact": "high",
                    "immediate_consequence": "帮助",
                    "narrative_impact": "good_end",
                },
                {
                    "id": "c2",
                    "text": "B",
                    "next": "bad",
                    "impact": "high",
                    "immediate_consequence": "离开",
                    "narrative_impact": "bad_end",
                },
            ],
            "after_lines_next": "",
            "is_ending": False,
        },
        "good": {"id": "good", "is_ending": True, "ending_type": "good", "choices": []},
        "bad": {"id": "bad", "is_ending": True, "ending_type": "bad", "choices": []},
    }
    errors = validate_outline_structure(nodes, "start", min_endings=3)
    assert any("至少需要 3 个" in err for err in errors)


def test_rejects_single_ending() -> None:
    nodes = {
        "start": {
            "id": "start",
            "after_lines_next": "only_end",
            "choices": [],
            "is_ending": False,
        },
        "only_end": {
            "id": "only_end",
            "is_ending": True,
            "ending_type": "good",
            "choices": [],
        },
    }
    errors = validate_outline_structure(
        nodes, "start", min_endings=3, choice_ratio_min=0.0, choice_ratio_max=1.0
    )
    assert any("结局节点仅 1 个" in err for err in errors)


def test_rejects_single_choice_on_node() -> None:
    nodes = _three_ending_outline()
    nodes["choice"]["choices"] = nodes["choice"]["choices"][:1]
    errors = validate_outline_structure(nodes, "start")
    assert any("仅 1 个选项" in err for err in errors)


def test_rejects_too_many_choices() -> None:
    nodes = _three_ending_outline()
    for extra_id, extra_next in (("c4", "good"), ("c5", "bad")):
        nodes["choice"]["choices"].append(
            {
                "id": extra_id,
                "text": extra_id.upper(),
                "next": extra_next,
                "impact": "low",
                "immediate_consequence": "x",
                "narrative_impact": f"y_{extra_id}",
            }
        )
    errors = validate_outline_structure(nodes, "start")
    assert any("选项过多" in err for err in errors)


def test_rejects_linear_only_graph() -> None:
    nodes: dict[str, dict] = {
        "start": {"id": "start", "after_lines_next": "s2", "choices": [], "is_ending": False}
    }
    for i in range(2, 10):
        nodes[f"s{i}"] = {
            "id": f"s{i}",
            "after_lines_next": f"s{i + 1}" if i < 9 else "",
            "choices": [],
            "is_ending": False,
        }
    nodes["s9"] = {
        "id": "s9",
        "after_lines_next": "",
        "choices": [
            {
                "id": "c1",
                "text": "好",
                "next": "good",
                "impact": "high",
                "immediate_consequence": "a",
                "narrative_impact": "good",
            },
            {
                "id": "c2",
                "text": "坏",
                "next": "bad",
                "impact": "high",
                "immediate_consequence": "b",
                "narrative_impact": "bad",
            },
        ],
        "is_ending": False,
    }
    nodes["good"] = {"id": "good", "is_ending": True, "ending_type": "good", "choices": []}
    nodes["bad"] = {"id": "bad", "is_ending": True, "ending_type": "bad", "choices": []}
    nodes["neutral"] = {"id": "neutral", "is_ending": True, "ending_type": "neutral", "choices": []}
    errors = validate_outline_structure(nodes, "start", min_choice_nodes=4)
    assert any("抉择点占比" in err or "抉择点仅" in err for err in errors)


def test_accepts_branchy_outline_with_min_choices() -> None:
    nodes = _branchy_outline(12)
    assert count_choice_nodes(nodes) >= 4
    errors = validate_outline_structure(nodes, "start", min_choice_nodes=4)
    assert errors == []


def test_count_choice_nodes() -> None:
    nodes = _three_ending_outline()
    assert count_choice_nodes(nodes) == 1


def test_relaxed_validation_allows_lower_choice_ratio() -> None:
    nodes = _three_ending_outline()
    errors = validate_outline_structure(nodes, "start", relaxed=True)
    assert errors == []


def test_outline_soft_pass_accepts_density_warnings() -> None:
    errors = [
        "抉择点占比 20% 不在 35%–65% 区间（1/5 个非结局节点含选项）",
        "高影响选项仅 1 个，至少需要 2 个（impact=high，导向不同路线/结局）",
    ]
    assert outline_soft_pass(errors, node_count=10) is True


def test_outline_soft_pass_rejects_unreachable() -> None:
    errors = ["不可达节点 2 个（如 scene_9）"]
    assert outline_soft_pass(errors, node_count=10) is False


def test_rejects_missing_impact_on_choices() -> None:
    nodes = _three_ending_outline()
    nodes["choice"]["choices"][0] = {
        "id": "c1",
        "text": "A",
        "next": "good",
        "immediate_consequence": "帮助",
        "narrative_impact": "good_end",
    }
    errors = validate_outline_structure(nodes, "start")
    assert any("impact（low/medium/high）" in err for err in errors)


def test_small_graph_one_choice_fails_ratio() -> None:
    """5 个非结局节点仅 1 个抉择点 → 20%，低于 35% 下限。"""
    nodes: dict[str, dict] = {
        "start": {"id": "start", "after_lines_next": "s2", "choices": [], "is_ending": False},
        "s2": {"id": "s2", "after_lines_next": "s3", "choices": [], "is_ending": False},
        "s3": {"id": "s3", "after_lines_next": "s4", "choices": [], "is_ending": False},
        "s4": {"id": "s4", "after_lines_next": "fork", "choices": [], "is_ending": False},
        "fork": {
            "id": "fork",
            "after_lines_next": "",
            "choices": [
                {
                    "id": "c1",
                    "text": "好",
                    "next": "good",
                    "impact": "high",
                    "immediate_consequence": "a",
                    "narrative_impact": "good",
                },
                {
                    "id": "c2",
                    "text": "坏",
                    "next": "bad",
                    "impact": "high",
                    "immediate_consequence": "b",
                    "narrative_impact": "bad",
                },
            ],
            "is_ending": False,
        },
        "good": {"id": "good", "is_ending": True, "ending_type": "good", "choices": []},
        "bad": {"id": "bad", "is_ending": True, "ending_type": "bad", "choices": []},
        "neutral": {"id": "neutral", "is_ending": True, "ending_type": "neutral", "choices": []},
    }
    errors = validate_outline_structure(nodes, "start")
    assert any("抉择点占比" in e and "20%" in e for e in errors)
