"""Tests for plot_beat / source excerpt mapping (改法一)."""

from __future__ import annotations

from document_extract import segment_text_for_slots
from source_context import build_node_source_contexts


def test_segment_by_chapters() -> None:
    parts = [f"第{i + 1}章\n\n" + ("甲" * 200) for i in range(12)]
    text = "\n\n".join(parts)
    segments = segment_text_for_slots(text, 4)
    assert len(segments) == 4
    assert all(len(s) > 100 for s in segments)


def test_build_node_contexts_maps_beats() -> None:
    beats = ["开端", "冲突", "高潮", "结局"]
    text = "第1章\n\n" + "开端内容。" * 50 + "\n\n第2章\n\n" + "冲突内容。" * 50
    node_ids = ["a", "b", "c", "d"]
    ctx = build_node_source_contexts(text, beats, node_ids, excerpt_limit=500)
    assert set(ctx.keys()) == set(node_ids)
    assert "对应情节节拍 #1" in ctx["a"]
    assert "原文节选" in ctx["a"]
    assert "开端" in ctx["a"]
