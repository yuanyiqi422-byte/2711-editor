import asyncio
import copy
import contextlib
import logging
import math
import os
import random
import re
import time
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

ProgressCallback = (
    Callable[..., Awaitable[None]] | None
)

from llm import (
    LLMError,
    chat_json,
    compute_timeout_sec,
    resolved_model_is_reasoning,
)
from graph_validate import (
    count_choice_nodes,
    outline_soft_pass,
    validate_choice_text_diversity,
    validate_outline_structure,
)
from scene_match import assign_node_backgrounds, extract_story_context
from models import (
    CharacterBrief,
    ChoiceOption,
    DialogueLine,
    EndingBlueprint,
    EmotionalBeatPoint,
    GamePack,
    derive_ending_choice_labels,
    derive_beat_choice_pair,
    enrich_node_choices,
    prepare_choice_dicts,
    StoryBible,
    StoryNode,
    STYLE_LABELS,
    StylePreset,
    _ENDING_MOOD_BY_TYPE,
    canonical_ending_type,
    derive_literary_ending_title,
    ending_type_label,
    normalize_ending_node_fields,
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
    compact_bible_dict,
    narrative_scale,
)
from source_context import (
    build_node_source_contexts,
    build_prev_scene_lines,
    compute_excerpt_limit,
)

# 超过此长度才二次切分；与 prompts 中 24-80 字/句对齐，避免切成 10 字碎片
MAX_LINE_CHARS = 100


def _env_int(name: str, default: str, *, lo: int = 1, hi: int | None = None) -> int:
    try:
        val = int(os.getenv(name, default))
    except ValueError:
        val = int(default)
    val = max(lo, val)
    if hi is not None:
        val = min(hi, val)
    return val


def _env_bool(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


SCENE_BATCH_SIZE = _env_int("SCENE_BATCH_SIZE", "8", lo=1, hi=10)
SCENE_BATCH_CONCURRENCY = _env_int("LLM_BATCH_CONCURRENCY", "5", lo=1, hi=6)
LLM_JSON_MAX_ATTEMPTS = _env_int("LLM_JSON_MAX_ATTEMPTS", "2", lo=1, hi=4)
OUTLINE_MAX_TOKENS = _env_int("OUTLINE_MAX_TOKENS", "5120", lo=2048, hi=16384)
SCENE_BATCH_MAX_TOKENS = _env_int("SCENE_BATCH_MAX_TOKENS", "6144", lo=2048, hi=16384)
OUTLINE_SOURCE_SAMPLE_CHARS = _env_int("OUTLINE_SOURCE_SAMPLE_CHARS", "1000", lo=0, hi=8000)
OUTLINE_BIBLE_ONLY_CHARS = _env_int("OUTLINE_BIBLE_ONLY_CHARS", "8000", lo=0, hi=100_000)
OUTLINE_FAST_MODEL = _env_bool("FAST_OUTLINE", "1")
SCENE_BATCH_FAST_MODEL = _env_bool("FAST_SCENES", "1")
BIBLE_FAST_MODEL = _env_bool("BIBLE_FAST_MODEL", "1")
def _narrative_fast_path_chars() -> int:
    raw = os.getenv("NARRATIVE_FAST_PATH_CHARS")
    if raw is not None and str(raw).strip():
        return _env_int("NARRATIVE_FAST_PATH_CHARS", "8000", lo=0, hi=50_000)
    return _env_int("SKIP_OUTLINE_BELOW_CHARS", "8000", lo=0, hi=50_000)


NARRATIVE_FAST_PATH_CHARS = _narrative_fast_path_chars()
SKIP_OUTLINE_BELOW_CHARS = NARRATIVE_FAST_PATH_CHARS
NARRATIVE_SPEED_MODE = os.getenv("NARRATIVE_SPEED_MODE", "").strip().lower()


SCENE_BATCH_DELAY_SEC = float(os.getenv("SCENE_BATCH_DELAY_SEC", "0"))
FALLBACK_BATCH_SIZE = _env_int("FALLBACK_BATCH_SIZE", "4", lo=2, hi=8)
PROGRESS_TICK_MIN_SEC = float(os.getenv("PROGRESS_TICK_MIN_SEC", "5"))
PROGRESS_TICK_MAX_SEC = float(os.getenv("PROGRESS_TICK_MAX_SEC", "8"))
SCENE_TIMEOUT_RETRIES = 2
OUTLINE_SKIP_MAX_CHARS = _env_int("OUTLINE_SKIP_MAX_CHARS", "20000", lo=0, hi=50_000)
OUTLINE_SKIP_MIN_BEATS = _env_int("OUTLINE_SKIP_MIN_BEATS", "6", lo=1, hi=20)


def _outline_max_attempts() -> int:
    if os.getenv("OUTLINE_ATTEMPTS") is not None:
        return _env_int("OUTLINE_ATTEMPTS", "1", lo=1, hi=2)
    return _env_int("OUTLINE_MAX_ATTEMPTS", "1", lo=1, hi=2)


OUTLINE_MAX_ATTEMPTS = _outline_max_attempts()
OUTLINE_TIMEOUT_FAIL_FAST = _env_bool("OUTLINE_TIMEOUT_FAIL_FAST", "1")


def _plot_beat_count(bible_dict: dict) -> int:
    return len([b for b in (bible_dict.get("plot_beats") or []) if str(b).strip()])


def _should_skip_outline_llm(char_count: int, bible_dict: dict) -> bool:
    """快路径仅跳过 LLM 大纲；结局/抉择校验仍在后续执行。"""
    if NARRATIVE_SPEED_MODE == "fast":
        return True
    beats = _plot_beat_count(bible_dict)
    if (
        OUTLINE_SKIP_MAX_CHARS > 0
        and char_count <= OUTLINE_SKIP_MAX_CHARS
        and beats >= OUTLINE_SKIP_MIN_BEATS
    ):
        return True
    if SKIP_OUTLINE_BELOW_CHARS > 0 and char_count < SKIP_OUTLINE_BELOW_CHARS:
        return True
    return False


def _outline_fail_fast(char_count: int) -> bool:
    """中短篇超时后立即回退节拍骨架，避免多次长等。"""
    return OUTLINE_TIMEOUT_FAIL_FAST and char_count <= OUTLINE_SKIP_MAX_CHARS
_GRAPH_PRESERVE_KEYS = ("choices", "after_lines_next", "is_ending", "ending_type")


def _valid_choice_dicts(choices: list) -> list[dict]:
    return prepare_choice_dicts(choices)


def _enrich_skeleton_choices(skeleton: dict, bible_dict: dict) -> None:
    """Ensure skeleton choice labels are beat-specific and not repeated across nodes."""
    avoid_signatures: set[tuple[str, ...]] = set()
    ending_labels = derive_ending_choice_labels(bible_dict)
    variant = 0
    for nid, raw in skeleton.items():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if not isinstance(choices, list) or len(choices) < 2:
            continue
        beat = str(raw.get("emotion_trigger") or raw.get("title") or nid)
        title = str(raw.get("title") or nid)
        fork_ending = any(
            isinstance(ch, dict) and str(ch.get("next") or "").startswith("ending_")
            for ch in choices
        )
        raw["choices"] = enrich_node_choices(
            [dict(c) for c in choices if isinstance(c, dict)],
            beat=beat,
            title=title,
            variant=variant,
            avoid_signatures=avoid_signatures,
            ending_labels=ending_labels if fork_ending else None,
        )
        variant += 1


def _enrich_pack_choices(
    nodes: dict[str, StoryNode],
    bible_dict: dict,
) -> dict[str, StoryNode]:
    avoid_signatures: set[tuple[str, ...]] = set()
    ending_labels = derive_ending_choice_labels(bible_dict)
    variant = 0
    out: dict[str, StoryNode] = {}
    for nid, node in nodes.items():
        if node.is_ending or len(node.choices) < 2:
            out[nid] = node
            continue
        beat = str(node.emotion_trigger or node.title or nid)
        fork_ending = any(str(ch.next or "").startswith("ending_") for ch in node.choices)
        enriched = enrich_node_choices(
            [c.model_dump() for c in node.choices],
            beat=beat,
            title=str(node.title or nid),
            variant=variant,
            avoid_signatures=avoid_signatures,
            ending_labels=ending_labels if fork_ending else None,
        )
        variant += 1
        out[nid] = node.model_copy(
            update={
                "choices": [
                    ChoiceOption.model_validate(c) for c in _valid_choice_dicts(enriched)
                ]
            }
        )
    return out


def _skeleton_graph_backup(skeleton: dict) -> dict[str, dict]:
    """Immutable snapshot of graph fields for post-batch restore."""
    backup: dict[str, dict] = {}
    for nid, raw in skeleton.items():
        if not isinstance(raw, dict):
            continue
        backup[nid] = {
            "choices": copy.deepcopy(raw.get("choices") or []),
            "after_lines_next": str(raw.get("after_lines_next") or ""),
            "is_ending": bool(raw.get("is_ending")),
            "ending_type": str(raw.get("ending_type") or ""),
            "title": str(raw.get("title") or nid),
            "lines": copy.deepcopy(raw.get("lines") or []),
        }
    return backup


def _finalize_scene_nodes(
    merged_nodes: dict[str, StoryNode],
    skeleton: dict,
    *,
    skeleton_backup: dict[str, dict] | None = None,
) -> dict[str, StoryNode]:
    """Restore skeleton graph structure when scene LLM strips or invalidates choices."""
    graph = skeleton_backup if skeleton_backup is not None else _skeleton_graph_backup(skeleton)
    out = dict(merged_nodes)
    for nid, skel_raw in graph.items():
        if not isinstance(skel_raw, dict):
            continue
        node = out.get(nid)
        skel_choices = _valid_choice_dicts(skel_raw.get("choices") or [])
        if node is None:
            data = dict(skel_raw)
            data["id"] = str(data.get("id") or nid)
            data["lines"] = data.get("lines") or [
                {"speaker": "旁白", "text": str(data.get("title") or nid)}
            ]
            data["choices"] = [
                ChoiceOption.model_validate(c) for c in skel_choices
            ]
            out[nid] = _normalize_node(StoryNode.model_validate(data))
            continue
        if node.is_ending:
            if skel_raw.get("is_ending"):
                raw_et = str(
                    skel_raw.get("ending_type") or node.ending_type or ""
                )
                raw_title = str(node.title or skel_raw.get("title") or nid)
                canon_et, clean_title = normalize_ending_node_fields(
                    is_ending=True,
                    ending_type=raw_et,
                    title=raw_title,
                )
                out[nid] = node.model_copy(
                    update={
                        "is_ending": True,
                        "ending_type": canon_et,
                        "title": clean_title,
                        "choices": [],
                        "after_lines_next": "",
                    }
                )
            else:
                node_choices = _valid_choice_dicts(
                    [c.model_dump() if hasattr(c, "model_dump") else c for c in node.choices]
                )
                if len(skel_choices) >= 2 and len(node_choices) < 2:
                    out[nid] = node.model_copy(
                        update={
                            "is_ending": False,
                            "ending_type": "",
                            "choices": [ChoiceOption.model_validate(c) for c in skel_choices],
                            "after_lines_next": "",
                        }
                    )
                else:
                    out[nid] = node.model_copy(
                        update={
                            "is_ending": False,
                            "ending_type": "",
                            "after_lines_next": str(skel_raw.get("after_lines_next") or ""),
                        }
                    )
            continue
        node_choices = _valid_choice_dicts(
            [c.model_dump() if hasattr(c, "model_dump") else c for c in node.choices]
        )
        if len(skel_choices) >= 2 and len(node_choices) < 2:
            out[nid] = node.model_copy(
                update={
                    "choices": [ChoiceOption.model_validate(c) for c in skel_choices],
                    "after_lines_next": "",
                }
            )
        elif not node_choices:
            skel_next = str(skel_raw.get("after_lines_next") or "").strip()
            if skel_next and skel_next in out:
                out[nid] = node.model_copy(update={"after_lines_next": skel_next})
    return out


def _merge_node_preserved_fields(skeleton_raw: dict, batch_item: dict) -> dict:
    """Merge batch LLM fields onto skeleton; keep graph keys when batch omits or strips them."""
    base = dict(skeleton_raw)
    for key, val in batch_item.items():
        if key not in _GRAPH_PRESERVE_KEYS:
            base[key] = val
    for key in _GRAPH_PRESERVE_KEYS:
        skel_val = skeleton_raw.get(key)
        batch_val = batch_item.get(key)
        if key == "choices":
            skel_choices = skel_val if isinstance(skel_val, list) else []
            batch_choices = batch_val if isinstance(batch_val, list) else []
            if len(batch_choices) >= 2:
                validated = _valid_choice_dicts(batch_choices)
                base["choices"] = validated if len(validated) >= 2 else copy.deepcopy(skel_choices)
            else:
                base["choices"] = copy.deepcopy(skel_choices)
            if len(base.get("choices") or []) >= 2:
                base["after_lines_next"] = ""
                node_id = str(base.get("id") or skeleton_raw.get("id") or "")
                beat = str(
                    skeleton_raw.get("emotion_trigger")
                    or skeleton_raw.get("title")
                    or batch_item.get("title")
                    or base.get("title")
                    or ""
                )
                title = str(
                    base.get("title")
                    or batch_item.get("title")
                    or skeleton_raw.get("title")
                    or ""
                )
                base["choices"] = enrich_node_choices(
                    prepare_choice_dicts(base.get("choices") or []),
                    beat=beat,
                    title=title,
                    variant=hash(node_id) % 16,
                    avoid_signatures=set(),
                )
        elif key == "is_ending":
            if skeleton_raw.get("is_ending"):
                base["is_ending"] = True
            else:
                base["is_ending"] = False
                base["ending_type"] = ""
        elif key == "ending_type":
            if not skeleton_raw.get("is_ending"):
                base["ending_type"] = ""
            else:
                merged_et = ""
                if batch_val not in (None, "", []):
                    merged_et = canonical_ending_type(str(batch_val))
                if not merged_et and skel_val not in (None, "", []):
                    merged_et = canonical_ending_type(str(skel_val))
                base["ending_type"] = merged_et
                if merged_et:
                    _, clean_title = normalize_ending_node_fields(
                        is_ending=True,
                        ending_type=merged_et,
                        title=str(base.get("title") or ""),
                    )
                    base["title"] = clean_title
        elif batch_val not in (None, "", []):
            base[key] = batch_val
        elif skel_val not in (None, "", []):
            base[key] = skel_val
    return base


def _outline_timeout_sec(char_count: int) -> float:
    if char_count < 8000:
        base = float(os.getenv("OUTLINE_LLM_TIMEOUT_SEC", "120"))
        return compute_timeout_sec(char_count, base_sec=base, min_sec=90.0, max_sec=240.0)
    if char_count < 15_000:
        base = float(os.getenv("OUTLINE_LLM_TIMEOUT_SEC", "150"))
        return compute_timeout_sec(char_count, base_sec=base, min_sec=120.0, max_sec=300.0)
    base = float(os.getenv("OUTLINE_LLM_TIMEOUT_SEC", "300"))
    return compute_timeout_sec(char_count, base_sec=base, min_sec=180.0, max_sec=900.0)


def _scene_timeout_sec(char_count: int, batch_len: int = 1, *, attempt: int = 0) -> float:
    base = float(os.getenv("SCENE_LLM_TIMEOUT_SEC", "420"))
    batch_factor = 1.0 + max(0, batch_len - 1) * 0.12
    scaled = compute_timeout_sec(
        char_count,
        base_sec=base * batch_factor,
        min_sec=240.0,
        max_sec=1200.0,
    )
    if attempt > 0:
        scaled = min(1200.0, scaled * (1.0 + 0.15 * attempt))
    return scaled


def _scene_timeout_error(
    *,
    completed: int,
    total: int,
    batch_len: int,
    waited_sec: float,
    attempt: int,
) -> str:
    retry_note = f"，第 {attempt + 1} 次尝试" if attempt > 0 else ""
    return (
        f"场景对白生成超时（进度 {completed}/{total}，本批 {batch_len} 个节点，"
        f"已等待>{int(waited_sec)}秒{retry_note}）。请直接重试创建；长文本可能需要更久。"
    )


def _is_truncated_json_llm_error(exc: BaseException) -> bool:
    if not isinstance(exc, LLMError):
        return False
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "json 不完整",
            "输出被截断",
            "输出不完整",
            "incomplete json",
            "truncated",
            "自动重试或拆分",
            "解释性文字而非 json",
            "而非 json",
        )
    )




def outline_progress_message(
    char_count: int,
    *,
    elapsed_sec: int,
    attempt: int,
    tick: int,
) -> str:
    del char_count, elapsed_sec
    templates = [
        "正在规划命运分支…",
        "AI 正在推演剧情树与结局线…",
        f"梳理抉择点与分支结构…（第 {attempt + 1} 轮规划）",
        "仍在规划命运分支，模型思考中…",
        "编排场景骨架与跳转关系…",
        "命运分支规划进行中，请耐心等待…",
    ]
    return templates[tick % len(templates)]


def scene_batch_progress_message(
    char_count: int,
    *,
    completed: int,
    total: int,
    elapsed_sec: int,
    tick: int,
) -> str:
    del char_count, elapsed_sec
    templates = [
        f"正在撰写场景对白 {completed}/{total}…",
        f"逐幕扩写剧情与选项 {completed}/{total}…",
        f"场景生成中 {completed}/{total}，模型仍在输出…",
        f"润色对白与立绘方向 {completed}/{total}…",
    ]
    return templates[tick % len(templates)]


async def _await_llm_task_with_progress(task, *, on_tick) -> object:
    elapsed = 0
    tick = 0
    try:
        while not task.done():
            wait_sec = random.uniform(PROGRESS_TICK_MIN_SEC, PROGRESS_TICK_MAX_SEC)
            _done, _ = await asyncio.wait({task}, timeout=wait_sec)
            if task.done():
                break
            elapsed += int(wait_sec)
            tick += 1
            await on_tick(elapsed, tick)
        return await task
    except asyncio.CancelledError:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        raise

def estimate_create_eta_label(char_count: int) -> str:
    """粗估整段创建流程耗时（供 SSE / 前端展示）。"""
    if char_count < 1500:
        return "约 1–2 分钟"
    if char_count < 4000:
        return "约 1–2 分钟"
    if char_count < 8000:
        return "约 1–3 分钟"
    if char_count < 15000:
        return "约 2–4 分钟"
    return "约 4–6 分钟"






def build_create_eta(char_count: int) -> dict:
    """SSE eta 载荷：展示标签 + narrative_scale 密度信息。"""
    scale = narrative_scale(char_count)
    return {
        "label": estimate_create_eta_label(char_count),
        "tier": scale["tier"],
        "nodes_min": scale["nodes_min"],
        "nodes_max": scale["nodes_max"],
        "nodes_range": scale["nodes_range"],
        "min_choice_moments": scale["min_choice_moments"],
        "endings_min": scale["endings_min"],
        "min_total_lines": scale["min_total_lines"],
        "max_total_lines": scale["max_total_lines"],
    }


def estimate_outline_remaining_hint(char_count: int) -> str:
    """命运分支规划阶段的剩余耗时提示。"""
    if char_count < 1500:
        return "预计还需 30 秒–1 分钟"
    if char_count < 4000:
        return "预计还需 1–2 分钟"
    if char_count < 8000:
        return "预计还需 1–3 分钟"
    if char_count < 15000:
        return "预计还需 2–4 分钟"
    if char_count < 22000:
        return "预计还需 1–3 分钟"
    return "预计还需 2–5 分钟"


def estimate_scene_batch_hint(char_count: int) -> str:
    """场景批次扩写阶段的耗时提示（55–72% 进度区间）。"""
    if char_count >= 12000:
        return "长文本场景生成可能需 2–4 分钟"
    if char_count >= 6000:
        return "场景生成可能需 1–3 分钟"
    return "场景生成通常还需 1–2 分钟"


def estimate_play_minutes(pack: GamePack) -> int:
    """按对白句数与场景数粗估游玩时长（分钟）。"""
    total_lines = sum(len(n.lines) for n in pack.nodes.values())
    node_count = len(pack.nodes)
    # 每句约 10–12 秒阅读+点击；场景切换约 8 秒
    seconds = total_lines * 11 + node_count * 8
    return max(1, round(seconds / 60))


def _parse_bible(raw: dict) -> StoryBible:
    chars = raw.get("characters") or []
    endings_raw = raw.get("endings") or []
    curve_raw = raw.get("emotional_curve") or []
    return StoryBible(
        title=str(raw.get("title") or "未命名故事").strip(),
        synopsis=str(raw.get("synopsis") or "").strip(),
        setting=str(raw.get("setting") or "").strip(),
        tone=str(raw.get("tone") or "").strip(),
        characters=[CharacterBrief.model_validate(c) for c in chars if isinstance(c, dict)],
        themes=[str(t) for t in (raw.get("themes") or []) if t],
        key_events=[str(e) for e in (raw.get("key_events") or []) if e],
        plot_beats=[str(b) for b in (raw.get("plot_beats") or []) if b],
        endings=[EndingBlueprint.model_validate(e) for e in endings_raw if isinstance(e, dict)],
        emotional_curve=[
            EmotionalBeatPoint.model_validate(p) for p in curve_raw if isinstance(p, dict)
        ],
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


def _parse_nodes(
    raw: dict,
    style: StylePreset,
    *,
    setting: str = "",
    era: str = "",
) -> GamePack:
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

    pack = GamePack(
        title=str(raw.get("title") or "互动叙事").strip(),
        style=style,
        style_label=STYLE_LABELS[style],
        synopsis=str(raw.get("synopsis") or "").strip(),
        start_node_id=start,
        nodes=nodes,
    )
    assign_node_backgrounds(
        pack.nodes,
        style,
        setting=setting,
        era=era,
        synopsis=pack.synopsis,
    )
    return pack


def _validate_graph(
    pack: GamePack,
    *,
    source_char_count: int = 0,
    relaxed: bool = False,
) -> None:
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
            if len(node.choices) < 2:
                raise LLMError(f"节点「{node.id}」分支节点至少需要 2 个 choices。")
            if len(node.choices) > 4:
                raise LLMError(f"节点「{node.id}」选项过多（{len(node.choices)}），最多 4 个。")
            for ch in node.choices:
                meta = (ch.narrative_impact or "").strip() or str(ch.impact or "").strip()
                if not meta:
                    raise LLMError(f"节点「{node.id}」选项「{ch.id}」缺少 narrative_impact/impact。")
                if ch.next not in pack.nodes:
                    raise LLMError(f"节点「{node.id}」选项指向未知节点「{ch.next}」。")
        elif nxt and nxt not in pack.nodes:
            raise LLMError(f"节点「{node.id}」的 after_lines_next 无效：{nxt}")

    scale = narrative_scale(source_char_count or len(pack.nodes) * 400)
    nodes_raw = {nid: n.model_dump() for nid, n in pack.nodes.items()}
    errors = validate_outline_structure(
        nodes_raw,
        pack.start_node_id,
        min_endings=int(scale.get("endings_min") or 3),
        min_choice_nodes=int(scale["min_choice_moments"]) if len(pack.nodes) >= 8 else 0,
        relaxed=relaxed,
    )
    branch_errors = [
        e
        for e in errors
        if any(k in e for k in ("抉择", "选项", "线性", "高影响", "伪分支"))
    ]
    if branch_errors:
        raise LLMError(f"剧情分支不足：{branch_errors[0]}")

    diversity_errors = validate_choice_text_diversity(nodes_raw)
    if diversity_errors:
        raise LLMError(f"抉择文案重复度过高：{diversity_errors[0]}")


def _batch_max_tokens(batch_len: int, *, attempt: int = 0) -> int:
    reasoning = resolved_model_is_reasoning(fast=SCENE_BATCH_FAST_MODEL)
    per_node = 1400 if reasoning else 1000
    cap = SCENE_BATCH_MAX_TOKENS
    if reasoning:
        cap = min(16384, max(cap, 8192))
    base = min(cap, max(2560, batch_len * per_node))
    if attempt > 0:
        return min(cap, int(base * (1.0 + 0.35 * attempt)))
    return base


def _bible_max_tokens() -> int:
    if resolved_model_is_reasoning(fast=BIBLE_FAST_MODEL):
        return min(16384, max(8192, _env_int("BIBLE_MAX_TOKENS", "8192", lo=4096, hi=16384)))
    return _env_int("BIBLE_MAX_TOKENS", "6144", lo=4096, hi=16384)


def _effective_batch_size(
    char_count: int,
    *,
    fast_path: bool = False,
    node_count: int = 0,
) -> int:
    """长文本用更大批次；快路径短篇尽量单批完成，减少 LLM 往返。"""
    reasoning = resolved_model_is_reasoning(fast=SCENE_BATCH_FAST_MODEL)
    reasoning_cap = 4 if reasoning else SCENE_BATCH_SIZE
    if fast_path and node_count > 0:
        return min(reasoning_cap, node_count)
    if reasoning:
        return max(2, min(4, reasoning_cap))
    if char_count >= 20_000:
        return min(10, SCENE_BATCH_SIZE + 2)
    if char_count >= 12_000:
        return min(10, SCENE_BATCH_SIZE + 1)
    if char_count >= 1500:
        return SCENE_BATCH_SIZE
    return max(3, min(5, SCENE_BATCH_SIZE - 2))


def _effective_batch_concurrency(char_count: int, *, fast_path: bool = False) -> int:
    """Default 5 concurrent scene LLM calls; long text up to 6."""
    if char_count >= 12_000:
        return min(6, SCENE_BATCH_CONCURRENCY + 2)
    if char_count >= 8000 or fast_path:
        return SCENE_BATCH_CONCURRENCY
    return max(2, SCENE_BATCH_CONCURRENCY - 1)


def _outline_source_sample_chars(char_count: int, bible_dict: dict) -> int:
    """长篇且圣经节拍充足时跳过大纲原文采样，仅依赖 bible。"""
    if OUTLINE_SOURCE_SAMPLE_CHARS <= 0:
        return 0
    beats = [b for b in (bible_dict.get("plot_beats") or []) if str(b).strip()]
    if OUTLINE_BIBLE_ONLY_CHARS > 0 and char_count >= OUTLINE_BIBLE_ONLY_CHARS and len(beats) >= 6:
        return 0
    return OUTLINE_SOURCE_SAMPLE_CHARS


def _scene_progress_pct(completed: int, total: int, *, batch_elapsed: int = 0) -> int:
    """52–72% 区间映射场景批量进度；batch_elapsed 用于批内细粒度推进。"""
    if total <= 0:
        return 55
    span = 20
    base = 52 + int(span * completed / total)
    if batch_elapsed > 0 and completed < total:
        est = max(45, min(120, 30 + total * 2))
        sub = int((span / total) * min(0.9, batch_elapsed / est))
        return min(72, base + max(1, sub))
    return min(72, base)


def _graph_parent_id(nid: str, skeleton: dict) -> str | None:
    for pid, raw in skeleton.items():
        if not isinstance(raw, dict):
            continue
        after = str(raw.get("after_lines_next") or "").strip()
        if after == nid:
            return str(pid)
        for ch in raw.get("choices") or []:
            if isinstance(ch, dict) and str(ch.get("next") or "").strip() == nid:
                return str(pid)
    return None


def _outline_bfs_layers(skeleton: dict, start_id: str) -> list[list[str]]:
    if not skeleton:
        return []
    start = start_id if start_id in skeleton else next(iter(skeleton))
    layers: list[list[str]] = []
    seen: set[str] = set()
    frontier = [start]
    while frontier:
        layer = [nid for nid in frontier if nid in skeleton and nid not in seen]
        if not layer:
            break
        layers.append(layer)
        seen.update(layer)
        nxt: list[str] = []
        nxt_seen: set[str] = set()
        for nid in layer:
            raw = skeleton.get(nid) or {}
            after = str(raw.get("after_lines_next") or "").strip()
            if after and after not in seen and after in skeleton and after not in nxt_seen:
                nxt.append(after)
                nxt_seen.add(after)
            for ch in raw.get("choices") or []:
                if not isinstance(ch, dict):
                    continue
                target = str(ch.get("next") or "").strip()
                if (
                    target
                    and target not in seen
                    and target in skeleton
                    and target not in nxt_seen
                ):
                    nxt.append(target)
                    nxt_seen.add(target)
        frontier = nxt
    orphans = [nid for nid in skeleton if nid not in seen]
    if orphans:
        layers.append(orphans)
    return layers


def _plan_scene_batches(
    skeleton: dict,
    start_id: str,
    batch_size: int,
) -> list[dict]:
    """线性段合并为大批次；同层分支可并行生成。"""
    layers = _outline_bfs_layers(skeleton, start_id)
    planned: list[dict] = []
    linear_buf: list[str] = []

    def _flush_linear() -> None:
        nonlocal linear_buf
        while linear_buf:
            chunk = linear_buf[:batch_size]
            linear_buf = linear_buf[batch_size:]
            planned.append({"parallel": False, "ids": chunk})

    for layer in layers:
        layer_ids = list(dict.fromkeys(layer))
        if len(layer_ids) > 1:
            _flush_linear()
            planned.append({"parallel": True, "ids": layer_ids})
        else:
            linear_buf.append(layer_ids[0])
            if len(linear_buf) >= batch_size:
                _flush_linear()
    _flush_linear()
    return planned


def _skeleton_from_bible(bible_dict: dict, source_char_count: int) -> tuple[dict, str]:
    """大纲失败时：用 plot_beats 生成线性骨架，走分批对白而非一次性生成。"""
    scale = narrative_scale(source_char_count)
    beats = [str(b).strip() for b in (bible_dict.get("plot_beats") or []) if str(b).strip()]
    if not beats:
        beats = [str(e).strip() for e in (bible_dict.get("key_events") or []) if str(e).strip()]
    if not beats:
        beats = ["开端", "发展", "高潮", "收束"]
    nodes_min = int(scale.get("nodes_min") or 8)
    nodes_max = int(scale.get("nodes_max") or nodes_min + 4)
    fallback_endings = 3
    beat_cap = max(4, nodes_max - fallback_endings)
    beat_floor = max(4, nodes_min - fallback_endings)
    target = min(beat_cap, max(len(beats), beat_floor))
    beats = beats[:target]
    while len(beats) < target:
        beats.append(f"过渡 {len(beats) + 1}")

    nodes: dict[str, dict] = {}
    ids: list[str] = []
    chapters = max(3, min(8, len(beats) // 3))
    for i, beat in enumerate(beats):
        nid = "start" if i == 0 else f"scene_{i + 1}"
        ids.append(nid)
        chapter = min(chapters, 1 + (i * chapters) // len(beats))
        nodes[nid] = {
            "id": nid,
            "title": beat[:24] or f"场景{i + 1}",
            "chapter": chapter,
            "chapter_title": f"第{chapter}章",
            "chapter_blurb": beat[:40] if i == 0 or i % max(1, len(beats) // chapters) == 0 else "",
            "scene_type": "intro" if i == 0 else ("climax" if i >= len(beats) - 2 else "buildup"),
            "mood": "neutral",
            "emotion_open": "",
            "emotion_trigger": beat[:60],
            "emotion_close": "",
            "emotion_action": "",
            "after_lines_next": "",
            "choices": [],
            "is_ending": False,
            "ending_type": "",
        }

    for i in range(len(ids) - 1):
        nodes[ids[i]]["after_lines_next"] = ids[i + 1]

    min_choices = int(scale.get("min_choice_moments") or 3)
    ratio_floor = math.ceil(len(ids) * 0.35) if len(ids) >= 4 else min_choices
    choice_target = max(min_choices, ratio_floor)
    mid_choices_needed = max(0, choice_target - 1)
    if len(ids) >= 4 and mid_choices_needed > 0:
        fork_idx = len(ids) - 1
        candidates = list(range(1, fork_idx))
        if len(candidates) > mid_choices_needed:
            step = len(candidates) / (mid_choices_needed + 1)
            pick_indices = sorted(
                {
                    min(candidates[-1], max(candidates[0], int(round(step * (i + 1)))))
                    for i in range(mid_choices_needed)
                }
            )
        else:
            pick_indices = candidates[:mid_choices_needed]
        for idx in pick_indices:
            if idx <= 0 or idx >= len(ids) - 1:
                continue
            nid = ids[idx]
            beat = beats[idx] if idx < len(beats) else nodes[nid]["title"]
            careful, bold = derive_beat_choice_pair(
                beat,
                nodes[nid]["title"],
                variant=idx,
            )
            nodes[nid]["after_lines_next"] = ""
            nodes[nid]["scene_type"] = "climax"
            nodes[nid]["choices"] = [
                {
                    "id": f"c_{nid}_careful",
                    "text": careful,
                    "next": ids[idx + 1],
                    "impact": "low",
                    "immediate_consequence": "气氛缓和，按原节拍推进",
                    "narrative_impact": "微调人物关系",
                    "relationship_delta": "0",
                },
                {
                    "id": f"c_{nid}_bold",
                    "text": bold,
                    "next": ids[min(idx + 2, len(ids) - 1)],
                    "impact": "medium",
                    "immediate_consequence": "跳过铺垫，直接进入下一冲突",
                    "narrative_impact": "改变后续场景节奏",
                    "relationship_delta": "+1",
                },
            ]

    fork_id = ids[-1]
    nodes[fork_id]["after_lines_next"] = ""
    nodes[fork_id]["scene_type"] = "climax"
    last_beat = beats[-1] if beats else "收束"
    ending_labels = derive_ending_choice_labels(bible_dict)
    careful, bold = derive_beat_choice_pair(last_beat, nodes[fork_id]["title"], variant=0)
    extra, _ = derive_beat_choice_pair(last_beat, nodes[fork_id]["title"], variant=1)
    fork_texts = ending_labels if ending_labels else [careful, bold, extra]
    nodes[fork_id]["choices"] = [
        {
            "id": "c_good",
            "text": fork_texts[0],
            "next": "ending_good",
            "impact": "high",
            "immediate_consequence": "做出最艰难但正确的选择",
            "narrative_impact": "走向温暖收束",
        },
        {
            "id": "c_bad",
            "text": fork_texts[1] if len(fork_texts) > 1 else bold,
            "next": "ending_bad",
            "impact": "high",
            "immediate_consequence": "回避冲突，关系破裂",
            "narrative_impact": "走向怅惘余韵",
        },
        {
            "id": "c_neutral",
            "text": fork_texts[2] if len(fork_texts) > 2 else extra,
            "next": "ending_neutral",
            "impact": "high",
            "immediate_consequence": "保留现状，得失参半",
            "narrative_impact": "归于平淡收场",
        },
    ]
    nodes[fork_id]["is_ending"] = False

    for ending_id, ending_type in (
        ("ending_good", "good"),
        ("ending_bad", "bad"),
        ("ending_neutral", "neutral"),
    ):
        ending_mood = _ENDING_MOOD_BY_TYPE.get(ending_type, "neutral")
        nodes[ending_id] = {
            "id": ending_id,
            "title": derive_literary_ending_title(
                ending_type,
                beat=last_beat,
                mood=ending_mood,
            ),
            "chapter": chapters,
            "chapter_title": f"第{chapters}章",
            "chapter_blurb": "",
            "scene_type": "ending",
            "mood": ending_mood,
            "emotion_open": "",
            "emotion_trigger": "",
            "emotion_close": "",
            "emotion_action": "",
            "after_lines_next": "",
            "choices": [],
            "is_ending": True,
            "ending_type": ending_type,
        }
    _enrich_skeleton_choices(nodes, bible_dict)
    return nodes, "start"


def _validate_fast_path_skeleton(
    skeleton: dict,
    start_id: str,
    source_char_count: int,
) -> list[str]:
    """快路径节拍骨架须通过结局/抉择结构校验（relaxed 仅放宽占比，不跳过结局）。"""
    scale = narrative_scale(source_char_count)
    return validate_outline_structure(
        skeleton,
        start_id,
        min_endings=int(scale.get("endings_min") or 3),
        min_choice_nodes=int(scale["min_choice_moments"]) if len(skeleton) >= 8 else 0,
        relaxed=True,
    )


def _merge_outline_with_skeleton(
    candidate: dict,
    bible_dict: dict,
    source_char_count: int,
) -> dict | None:
    """大纲接近可用时，用节拍骨架补齐结局/连通性，避免再跑一轮 LLM。"""
    nodes = candidate.get("nodes") if isinstance(candidate, dict) else None
    if not isinstance(nodes, dict) or len(nodes) < 4:
        return None
    start_id = str(candidate.get("start_node_id") or "start")
    merged_nodes = {nid: dict(raw) for nid, raw in nodes.items() if isinstance(raw, dict)}
    backup, _ = _skeleton_from_bible(bible_dict, source_char_count)
    scale = narrative_scale(source_char_count)
    min_endings = int(scale.get("endings_min") or 3)

    for eid, enode in backup.items():
        if isinstance(enode, dict) and enode.get("is_ending") and eid not in merged_nodes:
            merged_nodes[eid] = dict(enode)

    ending_types = {
        str(raw.get("ending_type") or "").strip()
        for raw in merged_nodes.values()
        if isinstance(raw, dict) and raw.get("is_ending")
    }
    if "good" not in ending_types or not ending_types.intersection({"bad", "neutral"}):
        for eid, enode in backup.items():
            if isinstance(enode, dict) and enode.get("is_ending"):
                merged_nodes[eid] = dict(enode)

    errors = validate_outline_structure(
        merged_nodes,
        start_id,
        min_endings=min_endings,
        min_choice_nodes=int(scale["min_choice_moments"]) if len(merged_nodes) >= 8 else 0,
        relaxed=True,
    )
    if not errors or outline_soft_pass(errors, len(merged_nodes)):
        patched = dict(candidate)
        patched["nodes"] = merged_nodes
        patched["start_node_id"] = start_id
        return patched
    return None


async def _run_scene_batch_resilient(
    batch_ids: list[str],
    *,
    chars: int,
    completed: int,
    total: int,
    run_batch: Callable[[list[str], int], Awaitable[dict]],
    on_tick: Callable[[int, int], Awaitable[None]],
    allow_split: bool = True,
) -> dict:
    last_msg = ""
    for attempt in range(SCENE_TIMEOUT_RETRIES + 1):
        if attempt == SCENE_TIMEOUT_RETRIES and allow_split and len(batch_ids) > 1:
            mid = len(batch_ids) // 2
            left = await _run_scene_batch_resilient(
                batch_ids[:mid],
                chars=chars,
                completed=completed,
                total=total,
                run_batch=run_batch,
                on_tick=on_tick,
                allow_split=False,
            )
            right = await _run_scene_batch_resilient(
                batch_ids[mid:],
                chars=chars,
                completed=completed,
                total=total,
                run_batch=run_batch,
                on_tick=on_tick,
                allow_split=False,
            )
            nodes: dict = {}
            for part in (left, right):
                nodes.update(part.get("nodes") or {})
            return {"nodes": nodes}

        timeout_sec = _scene_timeout_sec(chars, len(batch_ids), attempt=attempt)
        task = asyncio.create_task(run_batch(batch_ids, attempt))
        try:
            return await asyncio.wait_for(
                _await_llm_task_with_progress(task, on_tick=on_tick),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            last_msg = _scene_timeout_error(
                completed=completed,
                total=total,
                batch_len=len(batch_ids),
                waited_sec=timeout_sec,
                attempt=attempt,
            )
            logger.warning(
                "scene batch timed out attempt=%s batch=%s timeout=%.0fs",
                attempt + 1,
                batch_ids,
                timeout_sec,
            )
            if attempt < SCENE_TIMEOUT_RETRIES:
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            break
        except LLMError as exc:
            if not _is_truncated_json_llm_error(exc):
                raise
            last_msg = str(exc)
            logger.warning(
                "scene batch truncated JSON attempt=%s batch=%s",
                attempt + 1,
                batch_ids,
            )
            if attempt < SCENE_TIMEOUT_RETRIES:
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            break
    raise LLMError(last_msg or "场景对白生成失败，请直接重试。")


async def _run_scene_batches(
    *,
    bible_dict: dict,
    style: StylePreset,
    skeleton: dict,
    start_id: str,
    node_ids: list[str],
    node_contexts: dict[str, str],
    chars: int,
    report,
    batch_size_override: int | None = None,
    fast_path: bool = False,
) -> dict[str, StoryNode]:
    """Execute planned scene batches with parallel siblings, split-on-timeout, and heartbeat."""
    merged_nodes: dict[str, StoryNode] = {}
    merged_lines: dict[str, list] = {}
    skeleton_graph_backup = _skeleton_graph_backup(skeleton)
    total = len(node_ids)
    batch_size = batch_size_override or _effective_batch_size(
        chars, fast_path=fast_path, node_count=total
    )
    completed = 0
    planned_batches = _plan_scene_batches(skeleton, start_id, batch_size)

    await report(
        55,
        scene_batch_progress_message(chars, completed=0, total=total, elapsed_sec=0, tick=0),
        scene_completed=0,
        scene_total=total,
    )

    merge_lock = asyncio.Lock()
    concurrency = _effective_batch_concurrency(chars, fast_path=fast_path)
    sem = asyncio.Semaphore(concurrency)

    def _merge_batch_nodes(batch_nodes: dict) -> None:
        for nid, item in batch_nodes.items():
            if not isinstance(item, dict):
                continue
            skeleton_raw = skeleton.get(nid, {})
            if not isinstance(skeleton_raw, dict):
                skeleton_raw = {}
            base = _merge_node_preserved_fields(skeleton_raw, item)
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
            merged_lines[base["id"]] = [
                ln.model_dump() if hasattr(ln, "model_dump") else ln
                for ln in merged_nodes[base["id"]].lines
            ]

    def _graph_prev_lines(batch_ids: list[str]) -> dict[str, str]:
        prev_map: dict[str, str] = {}
        for nid in batch_ids:
            parent = _graph_parent_id(nid, skeleton)
            if not parent:
                continue
            lines = merged_lines.get(parent) or []
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
                if str(tx).strip():
                    parts.append(f"{sp}：{str(tx).strip()}")
            if parts:
                prev_map[nid] = "\n".join(parts)
        return prev_map

    async def _run_nodes_batch(batch_ids: list[str], attempt: int = 0) -> dict:
        prev_lines = build_prev_scene_lines(node_ids, batch_ids, merged_lines)
        if not prev_lines:
            prev_lines = _graph_prev_lines(batch_ids)
        timeout_sec = _scene_timeout_sec(chars, len(batch_ids), attempt=attempt)
        return await chat_json(
            build_nodes_batch_system(),
            build_nodes_batch_user(
                bible_dict,
                style,
                skeleton,
                batch_ids,
                source_char_count=chars,
                node_source_context=node_contexts,
                prev_scene_lines=prev_lines,
            ),
            temperature=0.52,
            max_tokens=_batch_max_tokens(len(batch_ids), attempt=attempt),
            fast_model=SCENE_BATCH_FAST_MODEL,
            timeout_sec=timeout_sec,
            step_label="场景对白",
            max_attempts=max(LLM_JSON_MAX_ATTEMPTS, 3),
            strict_json_mode=True,
        )

    async def _process_batch(batch_ids: list[str], *, parallel_layer: bool) -> None:
        nonlocal completed

        async def _run_one(ids: list[str]) -> None:
            nonlocal completed
            async with sem:
                batch_t0 = time.perf_counter()

                async def _batch_tick(elapsed: int, tick_n: int) -> None:
                    async with merge_lock:
                        done = completed
                    await report(
                        _scene_progress_pct(done, total, batch_elapsed=elapsed),
                        scene_batch_progress_message(
                            chars,
                            completed=done,
                            total=total,
                            elapsed_sec=elapsed,
                            tick=tick_n,
                        ),
                        scene_completed=done,
                        scene_total=total,
                    )

                batch_raw = await _run_scene_batch_resilient(
                    ids,
                    chars=chars,
                    completed=completed,
                    total=total,
                    run_batch=_run_nodes_batch,
                    on_tick=_batch_tick,
                )
                async with merge_lock:
                    _merge_batch_nodes(batch_raw.get("nodes") or {})
                    completed += len(ids)
                    done = completed

                logger.info(
                    "scene batch +%s nodes (%s/%s) %.1fs parallel=%s concurrency=%s",
                    len(ids),
                    done,
                    total,
                    time.perf_counter() - batch_t0,
                    parallel_layer,
                    concurrency,
                )
                await report(
                    _scene_progress_pct(done, total),
                    f"正在生成场景 {done}/{total}…",
                    scene_completed=done,
                    scene_total=total,
                )

        if parallel_layer and len(batch_ids) > 1:
            chunks = [
                batch_ids[i : i + batch_size]
                for i in range(0, len(batch_ids), batch_size)
            ]
            await asyncio.gather(*[_run_one(chunk) for chunk in chunks])
        else:
            await _run_one(batch_ids)

    for plan in planned_batches:
        batch_ids = plan["ids"]
        await _process_batch(batch_ids, parallel_layer=bool(plan.get("parallel")) and len(batch_ids) > 1)

        if SCENE_BATCH_DELAY_SEC > 0 and completed < total:
            await asyncio.sleep(SCENE_BATCH_DELAY_SEC)

    return _finalize_scene_nodes(
        merged_nodes,
        skeleton,
        skeleton_backup=skeleton_graph_backup,
    )


def _warn_if_sparse(pack: GamePack, source_char_count: int) -> None:
    scale = narrative_scale(source_char_count)
    expected_min = int(scale["nodes_min"])
    min_lines = int(scale["min_total_lines"])
    node_count = len(pack.nodes)
    total_lines = sum(len(n.lines) for n in pack.nodes.values())
    choice_nodes = count_choice_nodes(
        {nid: n.model_dump() for nid, n in pack.nodes.items()}
    )
    if source_char_count > 30_000 and node_count < expected_min:
        logger.warning(
            "生成场景偏少：原文 %s 字（%s），目标 %s 个场景，实际 %s 个。",
            f"{source_char_count:,}",
            scale["tier"],
            scale["nodes_range"],
            node_count,
        )
    if total_lines < min_lines:
        logger.warning(
            "对白偏少：目标至少 %s 句，实际 %s 句。",
            min_lines,
            total_lines,
        )
    if choice_nodes < int(scale["min_choice_moments"]):
        logger.warning(
            "抉择点偏少：目标至少 %s 个，实际 %s 个。",
            scale["min_choice_moments"],
            choice_nodes,
        )


async def _prepare_scene_generation(
    *,
    bible: StoryBible,
    source_text: str,
    skeleton: dict,
    start_id: str,
    chars: int,
) -> tuple[list[str], dict[str, str]]:
    layers = _outline_bfs_layers(skeleton, start_id)
    node_ids = [nid for layer in layers for nid in layer]
    if not node_ids:
        node_ids = list(skeleton.keys())
    excerpt_limit = compute_excerpt_limit(chars, len(bible.plot_beats or []))
    node_contexts = await asyncio.to_thread(
        build_node_source_contexts,
        source_text,
        bible.plot_beats,
        node_ids,
        source_char_count=chars,
        excerpt_limit=excerpt_limit,
    )
    return node_ids, node_contexts


async def analyze_story(
    text: str,
    style: StylePreset,
    source_char_count: int | None = None,
) -> StoryBible:
    full_chars = source_char_count if source_char_count is not None else len(text)
    use_fast = BIBLE_FAST_MODEL
    t0 = time.perf_counter()
    raw = await chat_json(
        build_bible_system(),
        build_bible_user(text, style, source_char_count=full_chars),
        temperature=0.6,
        max_tokens=_bible_max_tokens(),
        fast_model=use_fast,
        step_label="故事圣经",
        max_attempts=max(LLM_JSON_MAX_ATTEMPTS, 3),
    )
    logger.info(
        "analyze_story done %.1fs chars=%s fast=%s",
        time.perf_counter() - t0,
        full_chars,
        use_fast,
    )
    return _parse_bible(raw)


async def generate_game_nodes(
    bible: StoryBible,
    style: StylePreset,
    source_char_count: int = 0,
    source_text: str = "",
    on_progress: ProgressCallback = None,
) -> GamePack:
    async def report(
        pct: int,
        msg: str,
        *,
        scene_completed: int | None = None,
        scene_total: int | None = None,
        ending_count: int | None = None,
    ) -> None:
        if on_progress:
            await on_progress(
                pct,
                msg,
                scene_completed=scene_completed,
                scene_total=scene_total,
                ending_count=ending_count,
            )

    chars = source_char_count or max(len(bible.synopsis) * 20, 5000)
    bible_dict = compact_bible_dict(bible.model_dump())
    scale = narrative_scale(chars)
    min_endings = int(scale.get("endings_min") or 3)
    outline_sample_chars = _outline_source_sample_chars(chars, bible_dict)
    pipeline_t0 = time.perf_counter()
    use_outline_fast_path = _should_skip_outline_llm(chars, bible_dict)

    outline_raw = None
    last_outline_errors: list[str] = []
    use_fast_path = use_outline_fast_path

    if use_outline_fast_path:
        skeleton, start_id = _skeleton_from_bible(bible_dict, chars)
        fast_errors = _validate_fast_path_skeleton(skeleton, start_id, chars)
        if fast_errors:
            logger.warning(
                "快路径节拍骨架校验未通过（%s 条）: %s",
                len(fast_errors),
                fast_errors[:3],
            )
            last_outline_errors = fast_errors
        outline_title = bible.title
        outline_synopsis = bible.synopsis
        logger.info(
            "快路径：跳过 LLM 大纲（mode=%s），节拍骨架 %s 个场景",
            NARRATIVE_SPEED_MODE or "auto",
            len(skeleton),
        )
        await report(
            54,
            f"✓ 按情节节拍规划 · 共 {len(skeleton)} 幕",
        )
    else:
        await report(
            52,
            outline_progress_message(chars, elapsed_sec=0, attempt=0, tick=0),
        )

        async def _outline_with_heartbeat(attempt: int, *, timeout_sec: float) -> dict:
            task = asyncio.create_task(
                chat_json(
                    build_graph_outline_system(),
                    build_graph_outline_user(
                        bible_dict,
                        style,
                        source_char_count=chars,
                        source_text=source_text,
                        compact=True,
                        source_sample_chars=outline_sample_chars,
                        prior_errors=last_outline_errors if attempt > 0 else None,
                    ),
                    temperature=0.65,
                    max_tokens=OUTLINE_MAX_TOKENS,
                    fast_model=OUTLINE_FAST_MODEL,
                    timeout_sec=timeout_sec,
                    step_label="命运分支规划",
                    max_attempts=1,
                )
            )

            async def _on_tick(elapsed: int, tick: int) -> None:
                await report(
                    52,
                    outline_progress_message(
                        chars,
                        elapsed_sec=elapsed,
                        attempt=attempt,
                        tick=tick,
                    ),
                )

            return await _await_llm_task_with_progress(task, on_tick=_on_tick)

        for attempt in range(OUTLINE_MAX_ATTEMPTS):
            outline_timeout = _outline_timeout_sec(chars)
            try:
                candidate = await asyncio.wait_for(
                    _outline_with_heartbeat(attempt, timeout_sec=outline_timeout),
                    timeout=outline_timeout,
                )
            except asyncio.TimeoutError:
                logger.info("outline generation timed out attempt %s", attempt + 1)
                last_outline_errors = [
                    f"命运分支规划超时（已等待>{int(outline_timeout)}秒）。"
                    "改按情节节拍分批撰写。"
                ]
                break
            except LLMError as exc:
                logger.info("outline generation failed attempt %s: %s", attempt + 1, exc)
                last_outline_errors = [str(exc)]
                break
            skeleton = candidate.get("nodes") if isinstance(candidate, dict) else None
            start_id = str((candidate or {}).get("start_node_id") or "start")
            if not isinstance(skeleton, dict) or not skeleton:
                last_outline_errors = ["nodes 为空"]
                break
            errors = validate_outline_structure(
                skeleton,
                start_id,
                min_endings=min_endings,
                min_choice_nodes=int(scale["min_choice_moments"]) if len(skeleton) >= 8 else 0,
                relaxed=True,
            )
            if errors:
                last_outline_errors = errors
                logger.warning("outline 结构校验未通过: %s", errors[:3])
                if outline_soft_pass(errors, len(skeleton)):
                    logger.info("outline 软通过（%s 条非致命校验）", len(errors))
                    outline_raw = candidate
                    outline_ending_count = sum(
                        1 for n in skeleton.values() if isinstance(n, dict) and n.get("is_ending")
                    )
                    await report(
                        54,
                        f"✓ 命运分支 · {outline_ending_count} 种结局",
                        ending_count=outline_ending_count,
                    )
                    break
                merged = _merge_outline_with_skeleton(candidate, bible_dict, chars)
                if merged:
                    logger.info("outline 部分合并节拍骨架后采纳（%s 条校验）", len(errors))
                    outline_raw = merged
                    skeleton = merged["nodes"]
                    start_id = str(merged.get("start_node_id") or start_id)
                    outline_ending_count = sum(
                        1 for n in skeleton.values() if isinstance(n, dict) and n.get("is_ending")
                    )
                    await report(
                        54,
                        f"✓ 命运分支 · {outline_ending_count} 种结局",
                        ending_count=outline_ending_count,
                    )
                    break
                logger.info("outline 校验失败，立即回退节拍骨架")
                break
            outline_raw = candidate
            outline_ending_count = sum(
                1 for n in skeleton.values() if isinstance(n, dict) and n.get("is_ending")
            )
            await report(
                54,
                f"✓ 命运分支 · {outline_ending_count} 种结局",
                ending_count=outline_ending_count,
            )
            break
        else:
            if last_outline_errors:
                logger.info("outline 校验失败，回退节拍骨架: %s", last_outline_errors[:2])

        if outline_raw and isinstance(outline_raw.get("nodes"), dict) and outline_raw["nodes"]:
            skeleton = outline_raw["nodes"]
            start_id = str(outline_raw.get("start_node_id") or "start")
            outline_title = outline_raw.get("title") or bible.title
            outline_synopsis = outline_raw.get("synopsis") or bible.synopsis
        else:
            skeleton, start_id = _skeleton_from_bible(bible_dict, chars)
            outline_title = bible.title
            outline_synopsis = bible.synopsis
            use_fast_path = True
            logger.info(
                "outline 不可用，回退节拍骨架分批生成（%s 个场景）",
                len(skeleton),
            )
            await report(
                54,
                f"命运分支规划未完成，改按情节节拍分批撰写（共 {len(skeleton)} 幕）…",
            )

    skeleton_graph_backup = _skeleton_graph_backup(skeleton)

    node_ids, node_contexts = await _prepare_scene_generation(
        bible=bible,
        source_text=source_text,
        skeleton=skeleton,
        start_id=start_id,
        chars=chars,
    )
    scene_t0 = time.perf_counter()
    merged_nodes = await _run_scene_batches(
        bible_dict=bible_dict,
        style=style,
        skeleton=skeleton,
        start_id=start_id,
        node_ids=node_ids,
        node_contexts=node_contexts,
        chars=chars,
        report=report,
        fast_path=use_fast_path,
    )
    logger.info(
        "scene batches done %.1fs nodes=%s batches=%s",
        time.perf_counter() - scene_t0,
        len(merged_nodes),
        len(_plan_scene_batches(skeleton, start_id, _effective_batch_size(chars))),
    )
    logger.info("generate_game_nodes total %.1fs", time.perf_counter() - pipeline_t0)
    raw = {
        "title": outline_title,
        "synopsis": outline_synopsis,
        "start_node_id": start_id,
        "nodes": {nid: n.model_dump() for nid, n in merged_nodes.items()},
    }
    setting_blob, era_blob = extract_story_context(
        setting=bible.setting,
        synopsis=bible.synopsis,
        tone=bible.tone,
        themes=bible.themes,
    )
    pack = _parse_nodes(
        raw,
        style,
        setting=setting_blob,
        era=era_blob,
    )

    pack.characters = bible.characters
    if not pack.synopsis:
        pack.synopsis = bible.synopsis
    restored_nodes = _finalize_scene_nodes(
        dict(pack.nodes),
        skeleton,
        skeleton_backup=skeleton_graph_backup,
    )
    enriched_nodes = _enrich_pack_choices(restored_nodes, bible_dict)
    assign_node_backgrounds(
        enriched_nodes,
        style,
        setting=setting_blob,
        era=era_blob,
        synopsis=pack.synopsis,
    )
    pack = pack.model_copy(update={"nodes": enriched_nodes})
    _validate_graph(pack, source_char_count=chars, relaxed=use_fast_path)
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
                        ChoiceOption(
                            id=ch.id,
                            text=ch.text,
                            next=nxt,
                            consequence_hint=ch.consequence_hint,
                            immediate_consequence=ch.immediate_consequence,
                            narrative_impact=ch.narrative_impact,
                            relationship_delta=ch.relationship_delta,
                            impact=ch.impact,
                            weight=ch.weight,
                        )
                    )
                else:
                    new_choices.append(ch)
            merged[from_node] = node.model_copy(update={"choices": new_choices})

    pack = game.model_copy(update={"nodes": merged})
    setting_blob, era_blob = extract_story_context(
        setting=pack.synopsis,
        synopsis=pack.synopsis,
    )
    assign_node_backgrounds(
        pack.nodes,
        style,
        setting=setting_blob,
        era=era_blob,
        synopsis=pack.synopsis,
    )
    _validate_graph(pack)
    return pack
