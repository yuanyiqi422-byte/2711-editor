"""为分批对白生成匹配 plot_beat 与原文节选。"""

from __future__ import annotations

import os

from document_extract import segment_text_for_slots

DEFAULT_EXCERPT_CHARS = int(os.getenv("SCENE_EXCERPT_CHARS", "800"))
MAX_EXCERPT_CHARS = int(os.getenv("SCENE_EXCERPT_MAX_CHARS", "1600"))
PER_NODE_EXCERPT_CHARS = int(os.getenv("SCENE_EXCERPT_PER_NODE", "800"))


def compute_excerpt_limit(source_char_count: int, beat_count: int) -> int:
    """按原文字数与节拍数动态放大节选；单节点上限 PER_NODE_EXCERPT_CHARS。"""
    beats = max(int(beat_count or 0), 1)
    chars = max(int(source_char_count or 0), 400)
    per_beat = chars // beats
    dynamic = min(MAX_EXCERPT_CHARS, max(DEFAULT_EXCERPT_CHARS, per_beat // 2))
    return min(PER_NODE_EXCERPT_CHARS, dynamic)


def truncate_node_context(ctx: str, limit: int | None = None) -> str:
    """截断单节点原文节选块，保留节拍头与节选标记。"""
    text = (ctx or "").strip()
    if not text:
        return ""
    cap = limit if limit is not None else PER_NODE_EXCERPT_CHARS
    if len(text) <= cap:
        return text
    marker = "【原文节选"
    idx = text.find(marker)
    if idx < 0:
        return text[:cap].rstrip() + "……"
    head = text[: idx + len(marker)]
    rest = text[idx + len(marker) :]
    budget = max(120, cap - len(head) - 4)
    body = rest[:budget].rstrip() + "……"
    return head + body


def build_node_source_contexts(
    source_text: str,
    plot_beats: list[str],
    node_ids: list[str],
    *,
    source_char_count: int = 0,
    excerpt_limit: int | None = None,
) -> dict[str, str]:
    """按场景在图谱中的顺序，映射到 plot_beat 并附上对应原文节选。"""
    text = (source_text or "").strip()
    if not text or not node_ids:
        return {}

    beats = [b.strip() for b in (plot_beats or []) if b and str(b).strip()]
    if not beats:
        beats = ["主线情节"]

    limit = excerpt_limit if excerpt_limit is not None else compute_excerpt_limit(
        source_char_count or len(text), len(beats)
    )

    segments = segment_text_for_slots(text, len(beats))
    node_count = len(node_ids)
    beat_count = len(beats)
    contexts: dict[str, str] = {}

    for i, nid in enumerate(node_ids):
        beat_idx = min(int(i * beat_count / node_count), beat_count - 1) if node_count else 0
        beat = beats[beat_idx]
        excerpt = segments[beat_idx] if beat_idx < len(segments) else text
        if len(excerpt) > limit:
            excerpt = excerpt[:limit].rstrip() + "……"
        contexts[nid] = (
            f"【对应情节节拍 #{beat_idx + 1}】\n{beat}\n\n"
            f"【原文节选（请据此写对白，保留细节与语气，勿梗概化）】\n{excerpt}"
        )

    return contexts


def build_prev_scene_lines(
    node_ids: list[str],
    batch_ids: list[str],
    merged_lines: dict[str, list],
) -> dict[str, str]:
    """为 batch 中每个节点取上一场景末 2 句对白，保证衔接。"""
    prev_map: dict[str, str] = {}
    for nid in batch_ids:
        if nid not in node_ids:
            continue
        idx = node_ids.index(nid)
        if idx <= 0:
            continue
        prev_id = node_ids[idx - 1]
        lines = merged_lines.get(prev_id) or []
        if not lines:
            continue
        tail = lines[-2:] if len(lines) >= 2 else lines[-1:]
        parts: list[str] = []
        for ln in tail:
            if isinstance(ln, dict):
                sp = ln.get("speaker") or "旁白"
                tx = ln.get("text") or ""
            else:
                sp = getattr(ln, "speaker", "旁白")
                tx = getattr(ln, "text", "")
            if tx.strip():
                parts.append(f"{sp}：{tx.strip()}")
        if parts:
            prev_map[nid] = "\n".join(parts)
    return prev_map
