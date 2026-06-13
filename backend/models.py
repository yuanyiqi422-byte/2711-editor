import re
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

LITERARY_ENDING_FALLBACKS: dict[str, str] = {
    "good": "尘埃落定，各归其所",
    "bad": "风过无痕，徒留怅惘",
    "neutral": "潮起潮落，故事至此",
    "true": "真相昭然，万事同归",
    "hidden": "幽径独行，此中无人知",
    "open": "前路未竟，余音袅袅",
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

_SKELETON_ENDING_TITLE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "good": ("{snip}落定，曙光可期", "尘埃落定，各归其所", "晨曦微照，前路舒展"),
    "bad": ("{snip}成空，徒留怅惘", "风过无痕，天涯一别", "暮色四合，归途渺然"),
    "neutral": ("潮起潮落，故事至此", "{snip}已远，平淡收场", "云卷云舒，各安其所"),
    "true": ("真相昭然，万事同归", "{snip}揭晓，尘埃落定"),
    "hidden": ("幽径独行，此中无人知", "{snip}深处，秘而不宣"),
    "open": ("前路未竟，余音袅袅", "{snip}之后，故事仍续"),
}

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
    """User-facing / skeleton ending title: literary收束语, never 好/坏/普通结局."""
    canon = canonical_ending_type(ending_type)
    clean = sanitize_ending_node_title(title, canon)
    if clean and not is_moral_judgment_ending_title(clean):
        return clean[:16]
    beat_text = str(beat or "").strip()
    if beat_text:
        snip = _beat_snippet(beat, "", max_len=4)
        templates = _SKELETON_ENDING_TITLE_TEMPLATES.get(canon, ())
        if templates:
            idx = (hash(snip + canon + str(mood or "")) % len(templates) + len(templates)) % len(
                templates
            )
            result = templates[idx].format(snip=snip)
            return result[:16]
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
)

_BOLD_FALLBACK_LABELS: tuple[str, ...] = (
    "当面追问",
    "转身离开",
    "点头答应",
    "摇头拒绝",
    "直接离开",
)

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


def derive_beat_choice_pair(
    beat: str,
    title: str,
    *,
    variant: int = 0,
    avoid_signatures: set[tuple[str, ...]] | None = None,
) -> tuple[str, str]:
    """Rotate standalone careful/bold fallback labels; never inject beat fragments."""
    _ = beat, title  # kept for call-site compatibility
    avoid = avoid_signatures or set()
    n = len(_CAREFUL_FALLBACK_LABELS)
    for offset in range(n * 3):
        idx = (variant + offset) % n
        careful = _CAREFUL_FALLBACK_LABELS[idx]
        bold = _BOLD_FALLBACK_LABELS[idx % len(_BOLD_FALLBACK_LABELS)]
        if is_broken_choice_fragment(careful) or is_broken_choice_fragment(bold):
            continue
        sig = tuple(sorted(normalize_choice_text_key(t) for t in (careful, bold)))
        if len(sig) == 2 and sig not in avoid:
            return careful, bold
    return _CAREFUL_FALLBACK_LABELS[0], _BOLD_FALLBACK_LABELS[0]


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
) -> list[dict]:
    """Replace only empty/legacy generic choice labels; never overwrite specific LLM text."""
    if len(choices) < 2:
        return choices

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
        return out

    if len(out) >= 3 and ending_labels and len(ending_labels) >= len(out):
        for i in generic_indices:
            if i < len(ending_labels):
                out[i]["text"] = ending_labels[i]
    elif len(out) >= 2:
        careful, bold = derive_beat_choice_pair(
            beat,
            title,
            variant=variant,
            avoid_signatures=avoid_signatures,
        )
        pair_texts = (careful, bold)
        extra_offset = 0
        for i in generic_indices:
            if i < len(pair_texts):
                out[i]["text"] = pair_texts[i]
            else:
                extra, _ = derive_beat_choice_pair(
                    beat,
                    title,
                    variant=variant + extra_offset + 2,
                    avoid_signatures=avoid_signatures,
                )
                out[i]["text"] = extra
                extra_offset += 1
    new_sig = choice_text_set_signature(out)
    if new_sig:
        avoid_signatures.add(new_sig)
    return ensure_distinct_choice_texts(out, beat=beat, title=title, variant=variant)


def ensure_distinct_choice_texts(
    choices: list[dict],
    *,
    beat: str = "",
    title: str = "",
    variant: int = 0,
) -> list[dict]:
    """Ensure each choice in a node has a unique display label after sanitization."""
    if not choices:
        return []
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
        if not clean or key in seen:
            while fb_idx < len(_CAREFUL_FALLBACK_LABELS) * 6:
                careful, bold = derive_beat_choice_pair(
                    beat,
                    title,
                    variant=variant + fb_idx,
                )
                candidate = careful if fb_idx % 2 == 0 else bold
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
