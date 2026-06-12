"""Tests for scene batch planning and compact outline prompts."""

from __future__ import annotations

import json

from narrative_service import (
    _effective_batch_concurrency,
    _effective_batch_size,
    _outline_source_sample_chars,
    _plan_scene_batches,
    _should_skip_outline_llm,
    _skeleton_from_bible,
)
from prompts import build_graph_outline_user, compact_bible_dict, compact_skeleton_for_batch, narrative_scale
from source_context import truncate_node_context


def test_narrative_scale_short_text_not_forced_to_28_nodes() -> None:
    scale = narrative_scale(500)
    assert scale["nodes_min"] <= 12
    assert scale["min_total_lines"] < 50
    skeleton, _ = _skeleton_from_bible({"plot_beats": ["开端", "冲突", "结局"]}, 500)
    assert len(skeleton) <= 12


def test_compact_bible_smaller_than_full() -> None:
    bible = {
        "title": "测试",
        "synopsis": "梗概" * 40,
        "setting": "现代",
        "tone": "温暖",
        "characters": [{"name": "甲", "role": "主角", "trait": "善良"}],
        "themes": ["成长"],
        "key_events": ["事件1"],
        "plot_beats": [f"节拍{i}" for i in range(12)],
        "endings": [
            {
                "id": "good",
                "label": "好结局",
                "trigger_logic": "选择帮助",
                "key_nodes": ["s1"],
                "tone": "暖",
            }
        ],
        "emotional_curve": [{"position": "10%", "mood": "期待", "note": "开场"}],
    }
    full = len(json.dumps(bible, ensure_ascii=False))
    compact = len(json.dumps(compact_bible_dict(bible), ensure_ascii=False))
    assert compact <= full


def test_outline_user_uses_sample_not_full_source() -> None:
    bible = compact_bible_dict({"title": "T", "synopsis": "S", "plot_beats": ["a"]})
    long_source = "正文" * 10_000
    user = build_graph_outline_user(
        bible,
        "campus",
        source_char_count=20_000,
        source_text=long_source,
        compact=True,
        source_sample_chars=1500,
    )
    assert len(user) < len(long_source)
    assert "正文正文" in user


def test_plan_batches_merges_linear_layers() -> None:
    skeleton = {f"s{i}": {"after_lines_next": f"s{i + 1}"} for i in range(1, 7)}
    skeleton["s6"]["after_lines_next"] = ""
    skeleton["start"] = {"after_lines_next": "s1"}
    batches = _plan_scene_batches(skeleton, "start", batch_size=3)
    flat = [nid for b in batches for nid in b["ids"]]
    assert flat == ["start", "s1", "s2", "s3", "s4", "s5", "s6"]
    assert all(not b["parallel"] for b in batches)
    assert len(batches) == 3


def test_plan_batches_parallel_siblings() -> None:
    skeleton = {
        "start": {
            "choices": [
                {"id": "c1", "next": "path_a"},
                {"id": "c2", "next": "path_b"},
            ],
            "after_lines_next": "",
        },
        "path_a": {"after_lines_next": "merge"},
        "path_b": {"after_lines_next": "merge"},
        "merge": {"after_lines_next": ""},
    }
    batches = _plan_scene_batches(skeleton, "start", batch_size=4)
    parallel = [b for b in batches if b["parallel"]]
    assert len(parallel) == 1
    assert set(parallel[0]["ids"]) == {"path_a", "path_b"}
    flat = [nid for b in batches for nid in b["ids"]]
    assert flat.count("merge") == 1


def test_effective_batch_size_scales_for_long_text() -> None:
    assert _effective_batch_size(20_000) >= 8
    assert _effective_batch_size(3_000) == 8


def test_effective_batch_size_fast_path_single_batch() -> None:
    assert _effective_batch_size(2000, fast_path=True, node_count=8) == 8
    linear = {
        "start": {"id": "start", "after_lines_next": "s2", "choices": [], "is_ending": False},
        **{
            f"s{i}": {
                "id": f"s{i}",
                "after_lines_next": f"s{i + 1}" if i < 7 else "",
                "choices": [],
                "is_ending": i == 7,
            }
            for i in range(2, 8)
        },
    }
    batches = _plan_scene_batches(linear, "start", 8)
    assert len(batches) == 1


def test_effective_batch_concurrency_long_text() -> None:
    assert _effective_batch_concurrency(20_000) == 6
    assert _effective_batch_concurrency(8_000) == 5
    assert _effective_batch_concurrency(3_000) <= 5


def test_narrative_scale_20k_capped() -> None:
    scale = narrative_scale(20_000)
    assert scale["nodes_min"] >= 14
    assert scale["min_choice_moments"] >= 5
    assert scale["endings_min"] == 3
    assert scale["nodes_max"] <= 18


def test_narrative_scale_5k_compact() -> None:
    scale = narrative_scale(5_000)
    assert scale["nodes_min"] <= 10
    assert scale["nodes_max"] <= 12


def test_outline_bible_only_skips_source_sample() -> None:
    bible = {"plot_beats": [f"节拍{i}" for i in range(8)]}
    assert _outline_source_sample_chars(20_000, bible) == 0
    assert _outline_source_sample_chars(7_000, bible) > 0


def test_should_skip_outline_for_20k_with_six_beats() -> None:
    bible = {"plot_beats": [f"节拍{i}" for i in range(8)]}
    assert _should_skip_outline_llm(20_000, bible) is True
    assert _should_skip_outline_llm(5_000, bible) is True
    assert _should_skip_outline_llm(25_000, bible) is False


def test_should_skip_outline_requires_enough_beats_above_legacy_threshold() -> None:
    bible = {"plot_beats": ["开端", "冲突", "结局"]}
    assert _should_skip_outline_llm(5_000, bible) is True
    assert _should_skip_outline_llm(12_000, bible) is False


def test_compact_skeleton_strips_heavy_fields() -> None:
    skeleton = {
        "s1": {
            "id": "s1",
            "title": "开场",
            "scene_type": "intro",
            "image_prompt": "x" * 500,
            "lines": [],
            "after_lines_next": "s2",
        }
    }
    compact = compact_skeleton_for_batch(skeleton, ["s1"])
    assert "image_prompt" not in compact["s1"]
    assert compact["s1"]["title"] == "开场"


def test_truncate_node_context_caps_excerpt() -> None:
    ctx = "【对应情节节拍 #1】\n开端\n\n【原文节选（请据此写对白，保留细节与语气，勿梗概化）】\n" + ("字" * 3000)
    trimmed = truncate_node_context(ctx, 800)
    assert len(trimmed) <= 820
    assert trimmed.endswith("……")


def test_skeleton_from_bible_caps_excess_beats_for_short_text() -> None:
    bible = {"plot_beats": [f"节拍{i}" for i in range(30)], "key_events": []}
    skeleton, start_id = _skeleton_from_bible(bible, 500)
    assert start_id == "start"
    scale = narrative_scale(500)
    assert len(skeleton) <= int(scale["nodes_max"])


def test_skeleton_from_bible_builds_linear_chain() -> None:
    bible = {
        "plot_beats": [f"节拍{i}" for i in range(10)],
        "key_events": [],
    }
    skeleton, start_id = _skeleton_from_bible(bible, 20_000)
    assert start_id == "start"
    assert 14 <= len(skeleton) <= 18
    assert skeleton["start"]["after_lines_next"]
    ending = [n for n in skeleton.values() if n.get("is_ending")]
    assert len(ending) == 3
