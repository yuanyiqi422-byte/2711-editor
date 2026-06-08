import asyncio
import logging
import re
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], Awaitable[None]] | None

from llm import LLMError, chat_json
from models import (
    CharacterBrief,
    ChoiceOption,
    DialogueLine,
    GamePack,
    StoryBible,
    StoryNode,
    STYLE_LABELS,
    StylePreset,
)
from prompts import (
    build_bible_system,
    build_bible_user,
    build_expand_system,
    build_expand_user,
    build_graph_outline_system,
    build_graph_outline_user,
    build_nodes_batch_system,
    build_nodes_batch_user,
    build_nodes_system,
    build_nodes_user,
    narrative_scale,
)

logger = logging.getLogger(__name__)

# 超过此长度才二次切分；与 prompts 中 24-80 字/句对齐，避免切成 10 字碎片
MAX_LINE_CHARS = 100


def estimate_play_minutes(pack: GamePack) -> int:
    """按对白句数与场景数粗估游玩时长（分钟）。"""
    total_lines = sum(len(n.lines) for n in pack.nodes.values())
    node_count = len(pack.nodes)
    # 每句约 10–12 秒阅读+点击；场景切换约 8 秒
    seconds = total_lines * 11 + node_count * 8
    return max(1, round(seconds / 60))


def _parse_bible(raw: dict) -> StoryBible:
    chars = raw.get("characters") or []
    return StoryBible(
        title=str(raw.get("title") or "未命名故事").strip(),
        synopsis=str(raw.get("synopsis") or "").strip(),
        setting=str(raw.get("setting") or "").strip(),
        tone=str(raw.get("tone") or "").strip(),
        characters=[CharacterBrief.model_validate(c) for c in chars if isinstance(c, dict)],
        themes=[str(t) for t in (raw.get("themes") or []) if t],
        key_events=[str(e) for e in (raw.get("key_events") or []) if e],
        plot_beats=[str(b) for b in (raw.get("plot_beats") or []) if b],
    )


def _split_to_lines(text: str, default_speaker: str) -> list[DialogueLine]:
    chunks: list[str] = []
    for para in re.split(r"\n+", text.strip()):
        para = para.strip()
        if not para:
            continue
        sentences = re.split(r"(?<=[。！？…；.!?])", para)
        buf = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(buf) + len(s) <= MAX_LINE_CHARS:
                buf += s
            else:
                if buf:
                    chunks.append(buf)
                buf = s if len(s) <= MAX_LINE_CHARS else s[:MAX_LINE_CHARS]
        if buf:
            chunks.append(buf)

    if not chunks and text.strip():
        chunks = [text.strip()[:MAX_LINE_CHARS]]

    speaker = default_speaker or "旁白"
    portrait = "right" if speaker in ("你", "我") else ("none" if speaker == "旁白" else "left")
    return [
        DialogueLine(speaker=speaker, text=c, portrait=portrait)
        for c in chunks
    ]


def _normalize_node(node: StoryNode) -> StoryNode:
    lines_raw = node.lines or []
    lines: list[DialogueLine] = []
    for item in lines_raw:
        if isinstance(item, DialogueLine):
            line = item
        elif isinstance(item, dict):
            line = DialogueLine.model_validate(item)
        else:
            continue
        t = line.text.strip()
        if not t:
            continue
        if len(t) > MAX_LINE_CHARS:
            for sub in _split_to_lines(t, line.speaker or node.speaker or "旁白"):
                lines.append(sub)
        else:
            sp = line.speaker or node.speaker or "旁白"
            port = line.portrait or ("right" if sp in ("你", "我") else ("none" if sp == "旁白" else "left"))
            lines.append(DialogueLine(speaker=sp, text=t, portrait=port))

    if not lines and node.narrative.strip():
        lines = _split_to_lines(node.narrative, node.speaker or "旁白")

    if not lines:
        lines = [DialogueLine(speaker="旁白", text="……", portrait="none")]

    return node.model_copy(update={"lines": lines})


def _parse_nodes(raw: dict, style: StylePreset) -> GamePack:
    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, dict) or not nodes_raw:
        raise LLMError("模型未返回有效的 nodes 结构。")

    nodes: dict[str, StoryNode] = {}
    for nid, item in nodes_raw.items():
        if not isinstance(item, dict):
            continue
        data = dict(item)
        data["id"] = str(data.get("id") or nid)
        choices = data.get("choices") or []
        data["choices"] = [ChoiceOption.model_validate(c) for c in choices if isinstance(c, dict)]
        lines = data.get("lines") or []
        if lines:
            data["lines"] = [DialogueLine.model_validate(ln) for ln in lines if isinstance(ln, dict)]
        node = StoryNode.model_validate(data)
        nodes[data["id"]] = _normalize_node(node)

    start = str(raw.get("start_node_id") or "start")
    if start not in nodes:
        for candidate in ("start", "intro", "opening", "node_1", "scene_1"):
            if candidate in nodes:
                start = candidate
                break
        else:
            start = next(iter(nodes))

    return GamePack(
        title=str(raw.get("title") or "互动叙事").strip(),
        style=style,
        style_label=STYLE_LABELS[style],
        synopsis=str(raw.get("synopsis") or "").strip(),
        start_node_id=start,
        nodes=nodes,
    )


def _validate_graph(pack: GamePack) -> None:
    for node in pack.nodes.values():
        if node.is_ending:
            if node.choices:
                raise LLMError(f"结局节点「{node.id}」不应包含选项。")
            continue

        has_choices = len(node.choices) > 0
        nxt = (node.after_lines_next or "").strip()
        has_auto = bool(nxt and nxt in pack.nodes)

        if not has_choices and not has_auto:
            raise LLMError(
                f"节点「{node.id}」需设置 after_lines_next（自动进下一场景）或 choices（抉择点）。"
            )

        if has_choices:
            for ch in node.choices:
                if ch.next not in pack.nodes:
                    raise LLMError(f"节点「{node.id}」选项指向未知节点「{ch.next}」。")
        elif nxt and nxt not in pack.nodes:
            raise LLMError(f"节点「{node.id}」的 after_lines_next 无效：{nxt}")


def _nodes_max_tokens(source_char_count: int) -> int:
    if source_char_count > 80_000:
        return 16_384
    if source_char_count > 30_000:
        return 12_288
    return 8192


def _warn_if_sparse(pack: GamePack, source_char_count: int) -> None:
    scale = narrative_scale(source_char_count)
    expected_min = int(scale["nodes_min"])
    node_count = len(pack.nodes)
    if source_char_count > 30_000 and node_count < expected_min:
        logger.warning(
            "生成场景偏少：原文 %s 字（%s），目标 %s 个场景，实际 %s 个。"
            "建议用户重新「开始转化」；已优先通过 prompt 提升密度。",
            f"{source_char_count:,}",
            scale["tier"],
            scale["nodes_range"],
            node_count,
        )


async def analyze_story(
    text: str,
    style: StylePreset,
    source_char_count: int | None = None,
) -> StoryBible:
    full_chars = source_char_count if source_char_count is not None else len(text)
    raw = await chat_json(
        build_bible_system(),
        build_bible_user(text, style, source_char_count=full_chars),
        temperature=0.6,
        max_tokens=6144,
    )
    return _parse_bible(raw)


async def generate_game_nodes(
    bible: StoryBible,
    style: StylePreset,
    source_char_count: int = 0,
    on_progress: ProgressCallback = None,
) -> GamePack:
    async def report(pct: int, msg: str) -> None:
        if on_progress:
            await on_progress(pct, msg)

    chars = source_char_count or max(len(bible.synopsis) * 20, 5000)
    bible_dict = bible.model_dump()

    await report(52, "正在规划场景骨架…")

    try:
        outline_raw = await chat_json(
            build_graph_outline_system(),
            build_graph_outline_user(bible_dict, style, source_char_count=chars),
            temperature=0.65,
            max_tokens=4096,
        )
    except LLMError as exc:
        logger.info("outline generation failed, falling back: %s", exc)
        outline_raw = None

    if outline_raw and isinstance(outline_raw.get("nodes"), dict) and outline_raw["nodes"]:
        merged_nodes: dict[str, StoryNode] = {}
        skeleton = outline_raw["nodes"]
        node_ids = list(skeleton.keys())
        batch_size = 3
        total = len(node_ids)
        completed = 0
        for i in range(0, len(node_ids), batch_size):
            batch_ids = node_ids[i : i + batch_size]
            batch_raw = await chat_json(
                build_nodes_batch_system(),
                build_nodes_batch_user(
                    bible_dict, style, skeleton, batch_ids, source_char_count=chars
                ),
                temperature=0.78,
                max_tokens=4096,
            )
            batch_nodes = batch_raw.get("nodes") or {}
            for nid, item in batch_nodes.items():
                if not isinstance(item, dict):
                    continue
                base = dict(skeleton.get(nid, {}))
                base.update(item)
                base["id"] = str(base.get("id") or nid)
                choices = base.get("choices") or []
                base["choices"] = [
                    ChoiceOption.model_validate(c) for c in choices if isinstance(c, dict)
                ]
                lines = base.get("lines") or []
                if lines:
                    base["lines"] = [
                        DialogueLine.model_validate(ln) for ln in lines if isinstance(ln, dict)
                    ]
                merged_nodes[base["id"]] = _normalize_node(StoryNode.model_validate(base))
            completed += len(batch_ids)
            await report(
                55 + int(17 * completed / max(total, 1)),
                f"正在生成场景 {completed}/{total}…",
            )
            if i + batch_size < len(node_ids):
                await asyncio.sleep(1.2)

        raw = {
            "title": outline_raw.get("title") or bible.title,
            "synopsis": outline_raw.get("synopsis") or bible.synopsis,
            "start_node_id": outline_raw.get("start_node_id") or "start",
            "nodes": {nid: n.model_dump() for nid, n in merged_nodes.items()},
        }
        pack = _parse_nodes(raw, style)
    else:
        await report(58, "正在一次性生成场景节点…")
        raw = await chat_json(
            build_nodes_system(),
            build_nodes_user(bible_dict, style, source_char_count=chars),
            temperature=0.78,
            max_tokens=_nodes_max_tokens(chars),
        )
        pack = _parse_nodes(raw, style)

    pack.characters = bible.characters
    if not pack.synopsis:
        pack.synopsis = bible.synopsis
    _validate_graph(pack)
    _warn_if_sparse(pack, chars)
    return pack


async def expand_branch(
    text: str,
    style: StylePreset,
    game: GamePack,
    current_node_id: str,
    choice_id: str,
) -> GamePack:
    raw = await chat_json(
        build_expand_system(),
        build_expand_user(text, style, game.model_dump(), current_node_id, choice_id),
        temperature=0.8,
        max_tokens=6144,
    )
    new_nodes_raw = raw.get("nodes") or {}
    if not isinstance(new_nodes_raw, dict):
        raise LLMError("续写未返回有效节点。")

    merged = dict(game.nodes)
    for nid, item in new_nodes_raw.items():
        if not isinstance(item, dict):
            continue
        data = dict(item)
        data["id"] = str(data.get("id") or nid)
        choices = data.get("choices") or []
        data["choices"] = [ChoiceOption.model_validate(c) for c in choices if isinstance(c, dict)]
        lines = data.get("lines") or []
        if lines:
            data["lines"] = [DialogueLine.model_validate(ln) for ln in lines if isinstance(ln, dict)]
        merged[data["id"]] = _normalize_node(StoryNode.model_validate(data))

    for link in raw.get("updated_links") or []:
        if not isinstance(link, dict):
            continue
        from_node = str(link.get("from_node") or "")
        cid = str(link.get("choice_id") or "")
        nxt = str(link.get("next") or "")
        if from_node in merged and nxt in merged:
            node = merged[from_node]
            new_choices = []
            for ch in node.choices:
                if ch.id == cid:
                    new_choices.append(
                        ChoiceOption(id=ch.id, text=ch.text, next=nxt, consequence_hint=ch.consequence_hint)
                    )
                else:
                    new_choices.append(ch)
            merged[from_node] = node.model_copy(update={"choices": new_choices})

    pack = game.model_copy(update={"nodes": merged})
    _validate_graph(pack)
    return pack
