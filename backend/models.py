import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from document_extract import MAX_CREATE_CHARS

_TEXT_FIELD_KW: dict = {"min_length": 80}
if MAX_CREATE_CHARS > 0:
    _TEXT_FIELD_KW["max_length"] = MAX_CREATE_CHARS


StylePreset = Literal["xianxia", "urban_romance", "mystery", "campus"]

STYLE_LABELS: dict[str, str] = {
    "xianxia": "古风仙侠",
    "urban_romance": "都市言情",
    "mystery": "悬疑推理",
    "campus": "校园青春",
}

# ending_type 内部枚举（英文）→ UI / 节点 title 中文标签
ENDING_TYPE_CANONICAL = frozenset({"good", "bad", "neutral", "true", "hidden", "open"})

ENDING_TYPE_ALIASES: dict[str, str] = {
    "good": "good",
    "好": "good",
    "好结局": "good",
    "he": "good",
    "happy": "good",
    "bad": "bad",
    "坏": "bad",
    "坏结局": "bad",
    "be": "bad",
    "neutral": "neutral",
    "平和": "neutral",
    "平和结局": "neutral",
    "普通": "neutral",
    "普通结局": "neutral",
    "true": "true",
    "真": "true",
    "真结局": "true",
    "hidden": "hidden",
    "隐藏": "hidden",
    "隐藏结局": "hidden",
    "open": "open",
    "开放": "open",
    "开放结局": "open",
}

_LITERARY_ENDING_TITLE_POOL: dict[str, tuple[str, ...]] = {
    "good": (
        "青春就此落款",
        "误会终于冰释",
        "晨曦微照前程",
        "各得其所而安",
        "雨过天晴重逢",
        "前路仍向光明",
    ),
    "bad": (
        "风过徒留怅惘",
        "从此山高水长",
        "再无归期",
        "错付的情义",
        "暮色四合归途",
        "天涯一别难追",
    ),
    "neutral": (
        "晚风里的秘密",
        "云卷云舒各安",
        "潮起潮落至此",
        "生活回到寻常",
        "平淡收场也罢",
        "各安其所如是",
    ),
    "true": (
        "真相终于揭晓",
        "万事同归一处",
        "谜底水落石出",
        "一切尘埃落定",
        "昭然若揭之时",
        "迷雾散尽见真",
    ),
    "hidden": (
        "幽径独行无人知",
        "秘而不宣的终章",
        "极少人知的收束",
        "暗线于此闭合",
        "隐秘的另一种可能",
        "无人抵达的彼岸",
    ),
    "open": (
        "前路未竟余音在",
        "故事仍将继续",
        "余音袅袅未绝",
        "未完待续的明天",
        "开放式留白",
        "后话尚待书写",
    ),
}

LITERARY_ENDING_FALLBACKS: dict[str, str] = {
    canon: pool[0] for canon, pool in _LITERARY_ENDING_TITLE_POOL.items()
}

MORAL_JUDGMENT_ENDING_TITLES: frozenset[str] = frozenset(
    {"好结局", "坏结局", "普通结局", "平和结局"}
)

_ENDING_MOOD_BY_TYPE: dict[str, str] = {
    "good": "golden_dawn",
    "bad": "storm_sea",
    "neutral": "neutral",
    "true": "golden_dawn",
    "hidden": "dark_mystery",
    "open": "neon_rain",
}

_BROKEN_ENDING_TEMPLATE_RE = re.compile(
    r"^[\u4e00-\u9fff·…]{1,6}(?:已远，|成空，|落定，|揭晓，|深处，|之后，)"
    r"(?:平淡收场|徒留怅惘|曙光可期|尘埃落定|秘而不宣|故事仍续)$"
)

_RAW_ENDING_TITLE_RE = re.compile(
    r"^(good|bad|neutral|true|hidden|open)(?:[\s_\-·：:]+|(?=结局))(?:结局)?$",
    re.IGNORECASE,
)


def canonical_ending_type(raw: str) -> str:
    """Normalize LLM / title leakage into canonical English ending_type enum."""
    key = str(raw or "").strip().lower()
    if not key:
        return ""
    if key in ENDING_TYPE_ALIASES:
        return ENDING_TYPE_ALIASES[key]
    bare = re.sub(r"\s*结局\s*$", "", key).strip()
    if bare in ENDING_TYPE_ALIASES:
        return ENDING_TYPE_ALIASES[bare]
    m = _RAW_ENDING_TITLE_RE.match(key)
    if m:
        return m.group(1).lower()
    if key in ENDING_TYPE_CANONICAL:
        return key
    return ""


def is_moral_judgment_ending_title(title: str) -> bool:
    return str(title or "").strip() in MORAL_JUDGMENT_ENDING_TITLES


def is_raw_ending_type_title(title: str, ending_type: str = "") -> bool:
    t = str(title or "").strip().lower()
    if not t:
        return False
    if is_moral_judgment_ending_title(str(title or "").strip()):
        return True
    key = canonical_ending_type(ending_type) or str(ending_type or "").strip().lower()
    if key and (t == key or t == f"{key} 结局" or t == f"{key}结局"):
        return True
    bare = re.sub(r"\s*结局\s*$", "", t).strip()
    return bare in ENDING_TYPE_CANONICAL or bare in ENDING_TYPE_ALIASES


def sanitize_ending_node_title(title: str, ending_type: str = "") -> str:
    scene_title = str(title or "").strip()
    if not scene_title or is_raw_ending_type_title(scene_title, ending_type):
        return ""
    stripped = re.sub(
        r"^(good|bad|neutral|true|hidden|open)(?:[\s_\-·：:]+|(?=结局))",
        "",
        scene_title,
        flags=re.IGNORECASE,
    ).strip()
    if not stripped or stripped == "结局" or is_raw_ending_type_title(stripped, ending_type):
        return ""
    return stripped


def _trim_literary_ending_title(text: str, *, max_len: int = 12) -> str:
    t = re.sub(r"\s+", "", str(text or "").strip())
    if not t:
        return ""
    if len(t) <= max_len:
        return t
    chunk = t[:max_len]
    punct = max(chunk.rfind(p) for p in "，。！？、；：…")
    if punct >= 3:
        return chunk[: punct + 1]
    return chunk


def is_broken_ending_title(title: str) -> bool:
    """Reject beat-snippet拼接、模板残片、截断短语等非完整文学收束语."""
    clean = str(title or "").strip()
    if not clean or len(clean) < 4:
        return True
    if is_moral_judgment_ending_title(clean):
        return True
    if is_raw_ending_type_title(clean):
        return True
    if is_broken_choice_fragment(clean):
        return True
    compact = re.sub(r"\s+", "", clean)
    if _BROKEN_ENDING_TEMPLATE_RE.match(compact):
        return True
    if re.search(r"^[\u4e00-\u9fff]{2,5}已远", compact):
        return True
    return False


def ending_type_label(ending_type: str) -> str:
    """Mood-based literary fallback when no node title is available."""
    canon = canonical_ending_type(ending_type)
    return LITERARY_ENDING_FALLBACKS.get(canon, "故事至此收束")


def derive_literary_ending_title(
    ending_type: str,
    *,
    beat: str = "",
    mood: str = "",
    title: str = "",
) -> str:
    """User-facing / skeleton ending title: complete literary收束语, never beat-snippet拼接."""
    canon = canonical_ending_type(ending_type)
    clean = sanitize_ending_node_title(title, canon)
    if clean and not is_moral_judgment_ending_title(clean) and not is_broken_ending_title(clean):
        return _trim_literary_ending_title(clean)
    pool = _LITERARY_ENDING_TITLE_POOL.get(canon, ())
    if pool:
        beat_text = str(beat or "").strip()
        mood_text = str(mood or "").strip()
        if beat_text or mood_text:
            seed = f"{canon}|{mood_text}|{beat_text}"
            idx = (hash(seed) % len(pool) + len(pool)) % len(pool)
        else:
            idx = 0
        return pool[idx]
    return ending_type_label(canon)


def normalize_ending_node_fields(
    *,
    is_ending: bool,
    ending_type: str,
    title: str,
) -> tuple[str, str]:
    """Canonicalize ending_type and strip English enum leakage from node title."""
    if not is_ending:
        return "", title
    canon = canonical_ending_type(ending_type)
    if not canon and title:
        canon = canonical_ending_type(title)
    clean_title = sanitize_ending_node_title(title, canon)
    if clean_title and is_broken_ending_title(clean_title):
        clean_title = ""
    if not clean_title:
        clean_title = (
            derive_literary_ending_title(canon, title=title)
            if canon
            else str(title or "").strip()
        )
    return canon, clean_title


class CharacterBrief(BaseModel):
    name: str
    role: str = ""
    trait: str = ""


class EndingBlueprint(BaseModel):
    id: str
    label: str = ""
    trigger_logic: str = ""
    key_nodes: list[str] = Field(default_factory=list)
    tone: str = ""


class EmotionalBeatPoint(BaseModel):
    position: str = ""  # 如「全书25%」或章节描述
    mood: str = ""
    note: str = ""


class StoryBible(BaseModel):
    title: str
    synopsis: str
    setting: str = ""
    tone: str = ""
    characters: list[CharacterBrief] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    plot_beats: list[str] = Field(default_factory=list)
    endings: list[EndingBlueprint] = Field(default_factory=list)
    emotional_curve: list[EmotionalBeatPoint] = Field(default_factory=list)


ImpactLevel = Literal["low", "medium", "high"]

_CHOICE_TRAILING_PAREN_RE = re.compile(r"[（(][^）)]*[）)]\s*$")

CAREFUL_CHOICE_LABELS = ("暂且沉默", "先观望", "按兵不动", "委婉试探")
BOLD_CHOICE_LABELS = ("当面追问", "果断应允", "断然拒绝", "直接离开")

_FORMULAIC_CHOICE_RE = re.compile(r"徐徐图之|围绕.{0,12}图之")

_LEGACY_GENERIC_CHOICE_TEXTS = (
    "三思后回应",
    "谨慎试探",
    "徐徐图之",
    "按下疑虑",
    "果断抉择",
    "主动出击",
    "毅然行动",
    "铤而走险",
    "谨慎行事",
    "果断出击",
    "暂且观望",
    "直言不讳",
    "迂回试探",
)

GENERIC_CHOICE_TEXTS: frozenset[str] = frozenset(
    {
        *_LEGACY_GENERIC_CHOICE_TEXTS,
        "先观望",
        "果断应允",
        "沉默应对",
        "答应对方",
        "坚持本心",
        "选择离开",
        "接受妥协",
        "继续",
    }
)

_BEAT_SNIPPET_RE = re.compile(r"[，。！？、；：""''\s…—\-·]+")

# Enrich-only fallbacks: standalone verbs, never concatenate beat fragments.
_CAREFUL_FALLBACK_LABELS: tuple[str, ...] = (
    "沉默观察",
    "暂不表态",
    "按兵不动",
    "委婉试探",
    "暂且沉默",
    "沉默不语",
    "转移话题",
    "避而不答",
    "侧耳倾听",
    "低头沉思",
    "故作轻松",
    "退一步想",
)

_BOLD_FALLBACK_LABELS: tuple[str, ...] = (
    "当面追问",
    "转身离开",
    "点头答应",
    "摇头拒绝",
    "直接离开",
    "答应帮忙",
    "断然拒绝",
    "揭穿真相",
    "主动示好",
    "拂袖而去",
    "坚持己见",
    "冒险一试",
)

_EXTRA_UNIQUE_LABELS: tuple[str, ...] = (
    "轻声追问",
    "默然离去",
    "坦诚相告",
    "装作不知",
    "驻足观望",
    "试探开口",
    "岔开闲话",
    "索性直说",
    "暂且不理",
    "暗暗记下",
    "缓声相问",
    "转身回避",
    "点头应允",
    "摇头推辞",
    "上前一步",
    "退后半步",
    "压低声音",
    "抬眼对视",
    "移开视线",
    "握住对方的手",
    "松开手转身",
    "留下联系方式",
    "删除那条消息",
    "改天再谈",
    "此刻说清",
)

_STANDALONE_CHOICE_POOL: tuple[str, ...] = tuple(
    dict.fromkeys(
        _CAREFUL_FALLBACK_LABELS + _BOLD_FALLBACK_LABELS + _EXTRA_UNIQUE_LABELS
    )
)

MAX_CHOICE_TEXT_USES = 2

_BROKEN_CHOICE_FRAGMENT_RE = re.compile(
    r"(?:先|立刻)?(?:观望|介入).*(?:说|接|逾)"
    r"|^(?:沉默|观望|暂缓|试探)[\u4e00-\u9fff]{3,}$"
)


def sanitize_choice_display_text(text: str) -> str:
    """Strip trailing parenthetical outcome/hint leaks from choice button text."""
    s = str(text or "").strip()
    if not s:
        return s
    prev: str | None = None
    while prev != s:
        prev = s
        s = _CHOICE_TRAILING_PAREN_RE.sub("", s).strip()
    return s


def normalize_choice_text_key(text: str) -> str:
    s = sanitize_choice_display_text(text)
    return re.sub(r"\s+", "", s).lower()


_GENERIC_CHOICE_KEYS: frozenset[str] = frozenset(
    normalize_choice_text_key(t) for t in GENERIC_CHOICE_TEXTS
)


def is_generic_choice_text(text: str) -> bool:
    clean = sanitize_choice_display_text(text)
    if not clean:
        return True
    if is_formulaic_choice_text(clean):
        return True
    if is_broken_choice_fragment(clean):
        return True
    return normalize_choice_text_key(clean) in _GENERIC_CHOICE_KEYS


def is_formulaic_choice_text(text: str) -> bool:
    """Detect banned template phrasing like 徐徐图之 or 围绕…图之."""
    clean = sanitize_choice_display_text(text)
    if not clean:
        return False
    return bool(_FORMULAIC_CHOICE_RE.search(clean))


def is_broken_choice_fragment(text: str) -> bool:
    """Detect verb+beat-snippet garbage like 观望逾白说 or 先观望…说接近."""
    clean = sanitize_choice_display_text(text)
    if not clean:
        return True
    return bool(_BROKEN_CHOICE_FRAGMENT_RE.search(clean))


def choice_text_set_signature(choices: list) -> tuple[str, ...]:
    texts: list[str] = []
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        key = normalize_choice_text_key(str(ch.get("text") or ""))
        if key:
            texts.append(key)
    return tuple(sorted(texts))


_NODE_ID_RE = re.compile(r"^(scene|node|start|ending)[_\-]?\d*$", re.IGNORECASE)


def _beat_snippet(beat: str, title: str, *, max_len: int = 5) -> str:
    src = ""
    for candidate in (beat, title):
        chunk = str(candidate or "").strip()
        if not chunk or _NODE_ID_RE.match(chunk):
            continue
        src = chunk
        break
    if not src:
        src = "局势"
    src = _BEAT_SNIPPET_RE.sub("", src)
    if not src:
        return "局势"
    if len(src) <= max_len:
        return src
    mid = max(0, len(src) // 2 - max_len // 2)
    chunk = src[mid : mid + max_len]
    return chunk or src[:max_len]


def _choice_key_under_limit(key: str, used: Counter, max_uses: int) -> bool:
    return bool(key) and used.get(key, 0) < max_uses


def pick_choice_label(
    *,
    variant: int = 0,
    used_choice_keys: Counter | None = None,
    node_seen: set[str] | None = None,
    beat: str = "",
    title: str = "",
    max_uses: int = MAX_CHOICE_TEXT_USES,
) -> str:
    """Pick a short action label under per-game reuse cap and within-node uniqueness."""
    used = used_choice_keys if used_choice_keys is not None else Counter()
    seen = node_seen or set()
    pool = _STANDALONE_CHOICE_POOL
    n = len(pool)
    for offset in range(n * 3 + 12):
        label = pool[(variant + offset) % n]
        if is_broken_choice_fragment(label) or is_formulaic_choice_text(label):
            continue
        key = normalize_choice_text_key(label)
        if key in seen or not _choice_key_under_limit(key, used, max_uses):
            continue
        return label
    return _derive_unique_choice_label(
        beat,
        title,
        variant=variant,
        node_seen=seen,
        used_choice_keys=used,
        max_uses=max_uses,
    )


def _derive_unique_choice_label(
    beat: str,
    title: str,
    *,
    variant: int,
    node_seen: set[str],
    used_choice_keys: Counter,
    max_uses: int,
) -> str:
    """Beat/title-hash unique label for 3rd+ global duplicates (never drops nodes)."""
    snip = _beat_snippet(beat, title, max_len=4)
    seed = hash((beat, title, variant)) & 0xFFFF_FFFF
    actions = _EXTRA_UNIQUE_LABELS + _BOLD_FALLBACK_LABELS + _CAREFUL_FALLBACK_LABELS
    suffixes = ("", "片刻", "今夜", "此刻", "再说")
    for offset in range(len(actions) * len(suffixes) * 3):
        idx = (seed + variant + offset) % len(actions)
        action = actions[idx]
        suffix = suffixes[(seed + offset // len(actions)) % len(suffixes)]
        label = f"{action}{suffix}" if suffix else action
        if snip and offset % max(len(suffixes), 1) == 0:
            label = f"{action}·{snip}"
        if is_broken_choice_fragment(label) or is_formulaic_choice_text(label):
            continue
        key = normalize_choice_text_key(label)
        if key in node_seen or not _choice_key_under_limit(key, used_choice_keys, max_uses):
            continue
        return label[:16]
    fallback = actions[(seed + variant) % len(actions)]
    return fallback[:16]


def _bump_choice_keys(
    choices: list[dict],
    used_choice_keys: Counter,
) -> None:
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        key = normalize_choice_text_key(str(ch.get("text") or ""))
        if key:
            used_choice_keys[key] += 1


def derive_beat_choice_pair(
    beat: str,
    title: str,
    *,
    variant: int = 0,
    avoid_signatures: set[tuple[str, ...]] | None = None,
    used_choice_keys: Counter | None = None,
    max_uses: int = MAX_CHOICE_TEXT_USES,
) -> tuple[str, str]:
    """Rotate standalone careful/bold fallback labels; never inject beat fragments."""
    _ = beat, title  # kept for call-site compatibility in unique-label fallback
    avoid = avoid_signatures or set()
    used = used_choice_keys if used_choice_keys is not None else Counter()
    n = len(_CAREFUL_FALLBACK_LABELS)
    for offset in range(n * 4):
        idx = (variant + offset) % n
        careful = _CAREFUL_FALLBACK_LABELS[idx]
        bold = _BOLD_FALLBACK_LABELS[idx % len(_BOLD_FALLBACK_LABELS)]
        if is_broken_choice_fragment(careful) or is_broken_choice_fragment(bold):
            continue
        c_key = normalize_choice_text_key(careful)
        b_key = normalize_choice_text_key(bold)
        if c_key == b_key:
            continue
        if not _choice_key_under_limit(c_key, used, max_uses):
            continue
        if not _choice_key_under_limit(b_key, used, max_uses):
            continue
        sig = tuple(sorted((c_key, b_key)))
        if len(sig) == 2 and sig not in avoid:
            return careful, bold
    node_seen: set[str] = set()
    careful = pick_choice_label(
        variant=variant,
        used_choice_keys=used,
        node_seen=node_seen,
        beat=beat,
        title=title,
        max_uses=max_uses,
    )
    node_seen.add(normalize_choice_text_key(careful))
    bold = pick_choice_label(
        variant=variant + 1,
        used_choice_keys=used,
        node_seen=node_seen,
        beat=beat,
        title=title,
        max_uses=max_uses,
    )
    return careful, bold


def derive_ending_choice_labels(bible_dict: dict) -> list[str] | None:
    """Pull fork-ending labels from bible.endings when available."""
    endings = bible_dict.get("endings") or []
    labels: list[str] = []
    for item in endings:
        if not isinstance(item, dict):
            continue
        label = sanitize_choice_display_text(str(item.get("label") or ""))
        if label and not is_generic_choice_text(label):
            labels.append(label[:16])
    if len(labels) >= 3:
        return labels[:3]
    return None


def enrich_node_choices(
    choices: list[dict],
    *,
    beat: str,
    title: str,
    variant: int,
    avoid_signatures: set[tuple[str, ...]],
    ending_labels: list[str] | None = None,
    used_choice_signatures: Counter | None = None,
) -> list[dict]:
    """Replace only empty/legacy generic choice labels; never overwrite specific LLM text."""
    if len(choices) < 2:
        return choices

    used = used_choice_signatures if used_choice_signatures is not None else Counter()
    out = [dict(c) for c in choices if isinstance(c, dict)]
    generic_indices = [
        i
        for i, ch in enumerate(out)
        if is_generic_choice_text(str(ch.get("text") or ""))
    ]
    sig = choice_text_set_signature(out)
    if not generic_indices:
        if sig:
            avoid_signatures.add(sig)
        _bump_choice_keys(out, used)
        return out

    if len(out) >= 3 and ending_labels and len(ending_labels) >= len(out):
        for i in generic_indices:
            if i < len(ending_labels):
                label = ending_labels[i]
                key = normalize_choice_text_key(label)
                if not _choice_key_under_limit(key, used, MAX_CHOICE_TEXT_USES):
                    label = pick_choice_label(
                        variant=variant + i,
                        used_choice_keys=used,
                        node_seen={
                            normalize_choice_text_key(str(out[j].get("text") or ""))
                            for j in range(len(out))
                            if j != i
                        },
                        beat=beat,
                        title=title,
                    )
                out[i]["text"] = label
    elif len(out) >= 2:
        careful, bold = derive_beat_choice_pair(
            beat,
            title,
            variant=variant,
            avoid_signatures=avoid_signatures,
            used_choice_keys=used,
        )
        pair_texts = (careful, bold)
        extra_offset = 0
        for i in generic_indices:
            if i < len(pair_texts):
                out[i]["text"] = pair_texts[i]
            else:
                node_seen = {
                    normalize_choice_text_key(str(out[j].get("text") or ""))
                    for j in range(len(out))
                    if j != i
                }
                out[i]["text"] = pick_choice_label(
                    variant=variant + extra_offset + 2,
                    used_choice_keys=used,
                    node_seen=node_seen,
                    beat=beat,
                    title=title,
                )
                extra_offset += 1
    new_sig = choice_text_set_signature(out)
    if new_sig:
        avoid_signatures.add(new_sig)
    result = ensure_distinct_choice_texts(
        out,
        beat=beat,
        title=title,
        variant=variant,
        used_choice_signatures=used,
    )
    _bump_choice_keys(result, used)
    return result


def ensure_distinct_choice_texts(
    choices: list[dict],
    *,
    beat: str = "",
    title: str = "",
    variant: int = 0,
    used_choice_signatures: Counter | None = None,
) -> list[dict]:
    """Ensure each choice in a node has a unique display label after sanitization."""
    if not choices:
        return []
    used = used_choice_signatures if used_choice_signatures is not None else Counter()
    out: list[dict] = []
    seen: set[str] = set()
    fb_idx = 0
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        c = dict(ch)
        clean = sanitize_choice_display_text(str(c.get("text") or ""))
        imm = str(c.get("immediate_consequence") or "").strip()
        nar = str(c.get("narrative_impact") or "").strip()
        if clean and (clean == imm or clean == nar):
            clean = sanitize_choice_display_text(
                re.split(r"[（(]", str(c.get("text") or ""), maxsplit=1)[0].strip()
            )
        key = normalize_choice_text_key(clean)
        # Within-node only; global 3rd+ dedup is rewrite_graph_choice_text_frequency.
        needs_replace = not clean or key in seen
        if needs_replace:
            while fb_idx < len(_STANDALONE_CHOICE_POOL) * 8:
                candidate = pick_choice_label(
                    variant=variant + fb_idx,
                    used_choice_keys=used,
                    node_seen=seen,
                    beat=beat,
                    title=title,
                )
                fb_idx += 1
                ck = normalize_choice_text_key(candidate)
                if ck not in seen:
                    clean = candidate
                    key = ck
                    break
        seen.add(key)
        c["text"] = clean or "继续"
        out.append(c)
    return out


def rewrite_graph_choice_text_frequency(
    nodes: dict,
    *,
    max_uses: int = MAX_CHOICE_TEXT_USES,
    node_order: list[str] | None = None,
) -> None:
    """In-place: rewrite 3rd+ occurrence of the same normalized choice text."""
    order = node_order or sorted(nodes.keys())
    used: Counter = Counter()
    variant = 0
    for nid in order:
        raw = nodes.get(nid)
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if not isinstance(choices, list) or len(choices) < 2:
            continue
        beat = str(raw.get("emotion_trigger") or raw.get("title") or nid)
        title = str(raw.get("title") or nid)
        node_seen: set[str] = set()
        for ch in choices:
            if not isinstance(ch, dict):
                continue
            clean = sanitize_choice_display_text(str(ch.get("text") or ""))
            key = normalize_choice_text_key(clean)
            if (
                key
                and key not in node_seen
                and _choice_key_under_limit(key, used, max_uses)
            ):
                node_seen.add(key)
                used[key] += 1
                ch["text"] = clean
                continue
            replacement = _derive_unique_choice_label(
                beat,
                title,
                variant=variant,
                node_seen=node_seen,
                used_choice_keys=used,
                max_uses=max_uses,
            )
            variant += 1
            ch["text"] = replacement
            r_key = normalize_choice_text_key(replacement)
            node_seen.add(r_key)
            used[r_key] += 1


def prepare_choice_dicts(choices: list) -> list[dict]:
    """Validate, sanitize display text, and dedupe choice labels within one node."""
    validated: list[dict] = []
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        try:
            opt = ChoiceOption.model_validate(ch)
            validated.append(opt.model_dump())
        except Exception:
            continue
    return ensure_distinct_choice_texts(validated)


class ChoiceOption(BaseModel):
    id: str
    text: str
    next: str
    consequence_hint: str = ""
    immediate_consequence: str = ""
    narrative_impact: str = ""
    relationship_delta: str = ""
    impact: ImpactLevel = "medium"
    weight: int = Field(default=0, ge=0, le=3)

    @field_validator(
        "consequence_hint",
        "immediate_consequence",
        "narrative_impact",
        "relationship_delta",
        mode="before",
    )
    @classmethod
    def none_to_str(cls, v: object) -> object:
        return "" if v is None else v

    @field_validator("impact", mode="before")
    @classmethod
    def coerce_impact(cls, v: object) -> str:
        if v is None or v == "":
            return "medium"
        s = str(v).strip().lower()
        if s in ("low", "minor", "flavor", "small", "小"):
            return "low"
        if s in ("high", "major", "critical", "branch", "大", "关键"):
            return "high"
        if s in ("medium", "mid", "normal", "中"):
            return "medium"
        return "medium"

    @field_validator("weight", mode="before")
    @classmethod
    def coerce_weight(cls, v: object) -> int:
        if v is None or v == "":
            return 0
        try:
            w = int(v)
        except (TypeError, ValueError):
            return 0
        return max(0, min(3, w))

    @field_validator("text", mode="after")
    @classmethod
    def sanitize_choice_text(cls, v: str) -> str:
        s = sanitize_choice_display_text(v)
        return s or str(v or "").strip() or "继续"

    def resolved_impact(self) -> ImpactLevel:
        """显式 impact 优先；否则由 weight 或 narrative_impact 推断。"""
        if self.impact in ("low", "medium", "high"):
            if self.impact != "medium" or not self.weight:
                return self.impact
        if self.weight >= 3:
            return "high"
        if self.weight == 1:
            return "low"
        if self.weight == 2:
            return "medium"
        hint = (self.narrative_impact or "").lower()
        if any(k in hint for k in ("结局", "ending", "分支", "路线", "命运")):
            return "high"
        if any(k in hint for k in ("好感", "关系", "氛围", "语气", "微调")):
            return "low"
        return self.impact or "medium"


class DialogueLine(BaseModel):
    """橙光式单句对白，点击继续推进。"""

    speaker: str = ""
    text: str
    portrait: str = "none"  # none | left | right

    @field_validator("speaker", "portrait", mode="before")
    @classmethod
    def none_to_str(cls, v: object) -> object:
        return "" if v is None else v


class StoryNode(BaseModel):
    id: str
    title: str
    narrative: str = ""
    speaker: str = ""
    mood: str = "neutral"
    image_prompt: str = ""
    scene_id: str = ""
    bg_path: str = ""
    scene_type: str = "buildup"
    emotion_open: str = ""
    emotion_trigger: str = ""
    emotion_close: str = ""
    emotion_action: str = ""
    chapter: int = 1
    chapter_title: str = ""
    chapter_blurb: str = ""
    lines: list[DialogueLine] = Field(default_factory=list)
    after_lines_next: str = ""
    choices: list[ChoiceOption] = Field(default_factory=list)
    is_ending: bool = False
    ending_type: str = ""

    @field_validator("after_lines_next", mode="before")
    @classmethod
    def none_after_lines_next(cls, v: object) -> object:
        return "" if v is None else v

    @field_validator("choices", "lines", mode="before")
    @classmethod
    def none_to_list(cls, v: object) -> object:
        return [] if v is None else v

    @field_validator("is_ending", mode="before")
    @classmethod
    def none_to_bool(cls, v: object) -> object:
        return False if v is None else v

    @field_validator("ending_type", mode="before")
    @classmethod
    def normalize_ending_type(cls, v: object) -> object:
        if v is None:
            return ""
        return canonical_ending_type(str(v))

    @field_validator("chapter", mode="before")
    @classmethod
    def none_to_chapter(cls, v: object) -> object:
        return 1 if v is None else v


class GamePack(BaseModel):
    title: str
    style: StylePreset
    style_label: str
    synopsis: str
    start_node_id: str = "start"
    nodes: dict[str, StoryNode]
    characters: list[CharacterBrief] = Field(default_factory=list)

    @property
    def ending_count(self) -> int:
        return sum(1 for node in self.nodes.values() if node.is_ending)


class CreateGameRequest(BaseModel):
    text: str = Field(**_TEXT_FIELD_KW)
    style: StylePreset = "urban_romance"

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> str:
        return str(v).strip() if v is not None else ""


class ExpandNodeRequest(BaseModel):
    text: str = Field(**_TEXT_FIELD_KW)
    style: StylePreset
    game: GamePack
    current_node_id: str
    choice_id: str
