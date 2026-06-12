"""Match story nodes to scene PNG backgrounds (mirrors frontend/js/scene-images.js).

Matching hierarchy (highest → lowest influence)
------------------------------------------------
1. **Node text** — ``title``, ``image_prompt``, ``lines[].text`` (dialogue carries location cues).
2. **Story context** — bible ``setting`` / ``era`` / ``synopsis`` when provided to
   ``assign_node_backgrounds``.
3. **Keyword scores** — ``KEYWORD_SCORES`` from ``scene-images.js`` plus inverted
   ``scripts/scene-keywords.json`` tags.
4. **Semantic scene tags** — ``SCENE_TAG_WEIGHTS`` (ballroom, paris_street, …).
5. **Scene-type hints** — intro/buildup/climax … appended only when user text exists.
6. **Mood/style defaults** — +2 mood default, +1.5 style default on tied candidates.
7. **Pool fallback** — style pool hash pick by ``node_id`` when no keyword hits.
8. **Dedup** — penalize repeating the previous node's ``bg_path`` when alternatives exist.

Genre routing (``style`` preset + auto-detected overlays)
---------------------------------------------------------
- **campus** — classroom / sports / dorm pool; never period European streets unless era cues.
- **urban_romance** — city lights, cafe, office, apartment; ``period_fiction`` only on explicit
  19th-c. / Maupassant-era signals (not bare 巴黎 or 公寓+镜子).
- **mystery** (horror) — hospital, abandoned, fog, haunted; mirror → empress only in period context.
- **xianxia** — peaks, inn, sect, cave; European keywords suppressed.
- **scifi** (extended pool) — cyber, space, lab when keywords hit; else pool fallback.
- **period_fiction** (auto overlay) — European ballroom / pawnshop / candlelit assets via
  ``charity_gala`` → ``wedding_banquet_hall`` alias; down-ranks ``city_lights`` et al.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parent.parent


def _clean_path(path: str) -> str:
    return path.split("?", 1)[0] if path else path


SCENE_IMAGES_JS = ROOT / "frontend" / "js" / "scene-images.js"
MANIFEST = ROOT / "frontend" / "images" / "manifest.json"
SCENES_DIR = ROOT / "frontend" / "images" / "scenes"
SCENE_KEYWORDS = ROOT / "scripts" / "scene-keywords.json"

# Missing/broken asset ids → canonical scene (charity_gala PNG has protagonist overlay).
SCENE_ALIASES: dict[str, str] = {
    "charity_gala": "wedding_banquet_hall",
}

# Weight applied when a semantic tag matches node/story text.
SCENE_TAG_WEIGHTS: dict[str, dict[str, int]] = {
    "ballroom": {
        "wedding_banquet_hall": 9,
        "tribute_gift_hall": 7,
        "imperial_palace_hall": 5,
        "parent_meeting_hall": 3,
    },
    "banquet_hall": {
        "wedding_banquet_hall": 9,
        "tribute_gift_hall": 6,
        "family_dining": 4,
    },
    "mansion_interior": {
        "haunted_mansion_stair": 7,
        "ghost_mansion": 6,
        "manor_kneeling_punish": 6,
        "empress_bedchamber_empty": 5,
        "imperial_palace_hall": 4,
    },
    "paris_street": {
        "old_town_bridge_rain": 8,
        "canal_ancient_night": 8,
        "canal_twilight": 7,
        "clock_tower": 7,
        "market_alley": 6,
        "old_hometown_street": 5,
        "rainy_street": 3,
    },
    "modest_apartment": {
        "apartment_bedroom": 9,
        "insomnia_rental": 9,
        "candlelit_room": 8,
        "indoor_warm": 7,
        "landlord_doorway": 7,
        "laundry_room": 6,
        "family_dining": 5,
        "apartment_living": 8,
        "old_apartment_stairwell": 8,
        "candle_room": 6,
    },
    "jewelry": {
        "luxury_counter": 9,
        "auction_booth": 7,
        "pawnshop_ancient": 6,
        "pawnshop_alley_night": 5,
    },
    "19th_century": {
        "wedding_banquet_hall": 6,
        "clock_tower": 6,
        "old_town_bridge_rain": 6,
        "canal_ancient_night": 6,
        "escort_cart_road": 5,
        "execution_scaffold": 4,
        "candlelit_room": 5,
        "luxury_counter": 5,
        "pawnshop_ancient": 5,
    },
    "mirror_room": {
        "empress_unveil_night": 9,
        "empress_bedchamber_empty": 8,
        "apartment_bedroom": 7,
        "candlelit_room": 6,
        "candle_room": 5,
        "luxury_counter": 4,
    },
}

# Tag trigger phrases (longest match wins via tokenize + substring on blob).
TAG_TRIGGERS: dict[str, tuple[str, ...]] = {
    "ballroom": (
        "ballroom",
        "ball room",
        "舞会",
        "舞厅",
        "跳舞",
        "晚宴",
        "gala",
        "soirée",
        "soiree",
        "minister's ball",
        "embassy ball",
    ),
    "banquet_hall": ("banquet", "宴会", "喜宴", "酒席", "婚宴", "宴会厅", "banquet hall"),
    "mansion_interior": (
        "mansion",
        "manor",
        "府邸",
        "豪宅",
        "侯府",
        "大宅",
        "salon",
        "drawing room",
        "parlor",
        "客厅",
    ),
    "paris_street": (
        "paris street",
        "streets of paris",
        "paris boulevard",
        "paris at night",
        "塞纳河",
        "塞纳河畔",
        "seine river",
        "boulevard",
        "香榭",
        "champs-élysées",
        "champs elysees",
        "quai de",
    ),
    "modest_apartment": (
        "modest apartment",
        "small apartment",
        "apartment",
        "flat",
        "寒舍",
        "陋室",
        "出租",
        "公寓",
        "卧室",
        "简陋",
        "贫",
        "小房间",
        "阁楼",
        "garret",
        "attic room",
    ),
    "jewelry": (
        "necklace",
        "项链",
        "钻石",
        "珠宝",
        "首饰",
        "宝石",
        "diamond",
        "jewel",
        "jewelry",
        "jewellery",
        "pendant",
        "brooch",
        "bracelet",
    ),
    "19th_century": (
        "19th century",
        "19th-century",
        "nineteenth century",
        "十九世纪",
        "世纪巴黎",
        "1880",
        "1890",
        "1870",
        "maupassant",
        "莫泊桑",
        "belle époque",
        "belle epoque",
    ),
    "mirror_room": (
        "mirror",
        "镜子",
        "镜前",
        "梳妆",
        "dressing",
        "vanity",
        "looking glass",
    ),
}

# When period-fiction context is detected, down-rank generic modern city fallbacks.
GENERIC_URBAN_SCENES: frozenset[str] = frozenset(
    {
        "city_lights",
        "cyber_city_rain",
        "rainy_street",
        "subway_night",
        "crowded_subway",
        "city_park",
        "convenience_store_night",
        "night_bbq_street",
        "penthouse_night",
        "rooftop_sky",
    }
)

PERIOD_FICTION_PENALTY = 7.0
EUROPEAN_PERIOD_PENALTY = 6.0
REPEAT_BG_PENALTY = 8.0
TITLE_TEXT_WEIGHT = 1.5
LINES_TEXT_WEIGHT = 1.2

MODERN_CUES: tuple[str, ...] = (
    "现代",
    "当代",
    "21世纪",
    "今天",
    "上海",
    "北京",
    "深圳",
    "广州",
    "纽约",
    "new york",
    "地铁",
    "手机",
    "总裁",
    "校园",
    "大学",
    "公司",
    "写字楼",
    "赛博",
    "cyber",
    "smartphone",
    "wifi",
    "直播",
    "外卖",
)

HORROR_CUES: tuple[str, ...] = (
    "鬼",
    "诡异",
    "haunted",
    "ghost",
    "废弃",
    "诅咒",
    "阴魂",
    "怪谈",
    "惊悚",
    "太平间",
    "尸",
)

PERIOD_LOCATION_KEYWORDS: frozenset[str] = frozenset(
    {
        "europe",
        "欧洲",
        "paris",
        "巴黎",
        "victorian",
        "boulevard",
        "塞纳",
        "seine",
    }
)

PERIOD_SOFT_CUES: tuple[str, ...] = (
    "ballroom",
    "舞会",
    "舞厅",
    "gala",
    "soirée",
    "soiree",
    "晚宴",
    "necklace",
    "项链",
    "jewel",
    "jewelry",
    "pawnshop",
    "当铺",
    "寒舍",
    "陋室",
    "garret",
    "maupassant",
    "莫泊桑",
    "victorian",
    "belle époque",
    "belle epoque",
    "十九世纪",
    "19th century",
    "minister",
    "部长",
    "charity gala",
    "soirée",
)

PERIOD_CLUSTER_TAGS: tuple[str, ...] = ("ballroom", "banquet_hall", "jewelry")

MODEST_PERIOD_PHRASES: tuple[str, ...] = (
    "modest apartment",
    "small apartment",
    "寒舍",
    "陋室",
    "garret",
    "attic room",
    "阁楼",
)

SCENE_TYPE_HINTS: dict[str, str] = {
    "intro": "opening dawn peaceful entrance gate courtyard",
    "buildup": "street corridor room daily life home interior",
    "climax": "storm battle dramatic intense confrontation ballroom gala",
    "resolution": "sunset harbor calm meadow reunion modest home",
    "interlude": "quiet rest tea garden path apartment room",
    "ending": "sunset stars harbor ending farewell street home",
}

STYLE_SCENE_TYPE_HINTS: dict[str, dict[str, str]] = {
    "campus": {
        "intro": "school gate campus courtyard morning cherry blossom",
        "buildup": "classroom library dorm corridor cafeteria campus field",
        "climax": "rooftop confession exam hall sports festival",
        "resolution": "graduation campus sunset reunion",
        "interlude": "club room library aisle dorm hallway",
        "ending": "campus farewell cherry tunnel graduation",
    },
    "xianxia": {
        "intro": "mountain gate sect entrance mist peaks",
        "buildup": "bamboo grove inn courtyard cultivation hall",
        "climax": "tribulation peak duel sect arena",
        "resolution": "lotus pond hot spring reunion valley",
        "interlude": "meditation cave shrine path ferry",
        "ending": "cloud sea farewell immortal peak",
    },
    "mystery": {
        "intro": "fog alley crime scene entrance",
        "buildup": "hospital corridor mansion stair study",
        "climax": "abandoned building confrontation morgue",
        "resolution": "courtroom police mediation reveal",
        "interlude": "quiet investigation archive room",
        "ending": "rainy street farewell mystery resolve",
    },
    "period_fiction": {
        "intro": "carriage arrival modest street candlelit",
        "buildup": "apartment mirror salon pawnshop",
        "climax": "ballroom banquet gala necklace",
        "resolution": "bridge rain canal modest home",
        "interlude": "landlord doorway laundry candle room",
        "ending": "old town farewell modest apartment",
    },
    "urban_romance": {
        "intro": "city apartment rainy commute",
        "buildup": "cafe office elevator street date",
        "climax": "rooftop confrontation rain confession",
        "resolution": "balcony sunset reunion apartment",
        "interlude": "convenience store night walk",
        "ending": "city lights farewell harbor",
    },
}

NON_URBAN_STYLES: frozenset[str] = frozenset(
    {"campus", "xianxia", "period_fiction", "mystery", "horror", "scifi"}
)

SETTING_CONTEXT_WEIGHT = 2

STYLE_POOLS: dict[str, list[str]] = {
    "xianxia": [
        "xianxia_peaks",
        "pagoda_mist",
        "jianghu_inn",
        "bamboo_grove",
        "shrine_path",
        "ancient_inn_courtyard",
        "lotus_pond_dawn",
        "cloud_sea_stairway",
        "imperial_palace_hall",
        "sect_arena",
        "hot_spring_mist",
        "sword_lake_mirror",
        "ancient_market_square",
        "ferry_crossing_mist",
        "tribulation_cloud_vortex",
    ],
    "urban_romance": [
        "city_lights",
        "rainy_street",
        "romance_cafe",
        "balcony_night",
        "apartment_elevator",
        "convenience_store_night",
        "subway_night",
        "hotel_lobby",
        "beach_date_sunset",
        "shopping_mall_atrium",
        "office_midnight",
        "rooftop_sky",
        "bus_stop_rain",
        "blind_date_restaurant",
        "night_bbq_street",
    ],
    "mystery": [
        "mystery_fog",
        "crime_tape_alley",
        "ghost_mansion",
        "morgue_corridor_blue",
        "haunted_mansion_stair",
        "abandoned_hospital",
        "rainy_street",
        "courtroom",
        "police_mediation",
        "ghost_village_fog",
        "hospital_hall",
        "blackout_study_hall",
        "funeral_hall_empty",
        "canal_ancient_night",
        "parking_ambush",
    ],
    "campus": [
        "campus_field",
        "school_corridor",
        "classroom_drowse",
        "rooftop_sky",
        "library_aisle",
        "cafeteria_serving",
        "exam_hall_silent",
        "sunny_basketball",
        "cherry_tunnel",
        "dormitory_hallway_night",
        "art_room",
        "grad_backstage",
        "library_roof_study",
        "sports_parade",
        "blackout_study_hall",
    ],
    "period_fiction": [
        "wedding_banquet_hall",
        "tribute_gift_hall",
        "candlelit_room",
        "luxury_counter",
        "old_town_bridge_rain",
        "canal_ancient_night",
        "clock_tower",
        "insomnia_rental",
        "landlord_doorway",
        "pawnshop_ancient",
        "family_dining",
        "indoor_warm",
        "empress_bedchamber_empty",
        "empress_unveil_night",
        "apartment_bedroom",
        "haunted_mansion_stair",
        "auction_booth",
        "market_alley",
        "laundry_room",
        "candle_room",
        "apartment_living",
        "old_apartment_stairwell",
        "canal_twilight",
        "escort_cart_road",
    ],
    "scifi": [
        "cyber_city_rain",
        "ai_data_core",
        "space_station_window",
        "mars_base_dome",
        "colosseum_cyber_arm",
        "cyberpunk_alley_gun",
        "mech_hangar_weld",
        "bio_lab_embryo",
        "wasteland_radar",
        "submarine_sonar",
        "observatory",
        "infinite_white_orb",
        "bunker_red_alarm",
        "warship_planet_burst",
        "sky_tram",
    ],
    "horror": [
        "abandoned_hospital",
        "haunted_mansion_stair",
        "ghost_mansion",
        "morgue_corridor_blue",
        "hospital_blood_elevator",
        "ghost_village_fog",
        "haunted_toilet_crack",
        "curse_bamboo_night",
        "cursed_bus_ride",
        "ghost_wedding_hall",
        "paper_doll_village",
        "funeral_hall_empty",
        "ghost_story_well",
        "crime_tape_alley",
        "mystery_fog",
    ],
}

STYLE_DEFAULTS: dict[str, str] = {
    "xianxia": "xianxia_peaks",
    "urban_romance": "city_lights",
    "mystery": "mystery_fog",
    "campus": "campus_field",
    "period_fiction": "candlelit_room",
    "scifi": "cyber_city_rain",
    "horror": "abandoned_hospital",
}

EUROPEAN_PERIOD_SCENES: frozenset[str] = frozenset(
    set(SCENE_TAG_WEIGHTS.get("paris_street", {}))
    | set(SCENE_TAG_WEIGHTS.get("19th_century", {}))
    | {"clock_tower", "wedding_banquet_hall", "tribute_gift_hall", "candlelit_room", "luxury_counter"}
)


def _parse_js_map(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"^\s+(\w+):\s*\"([^\"]+)\"", block, re.M):
        out[m.group(1)] = m.group(2)
    return out


def _parse_keyword_scores(block: str) -> dict[str, dict[str, int]]:
    scores: dict[str, dict[str, int]] = {}
    for m in re.finditer(r'"([^"]+)":\s*\{([^}]+)\}', block):
        weights: dict[str, int] = {}
        for w in re.finditer(r"(\w+):\s*(\d+)", m.group(2)):
            weights[w.group(1)] = int(w.group(2))
        if weights:
            scores[m.group(1)] = weights
    return scores


def _invert_scene_keywords(raw: dict) -> dict[str, dict[str, int]]:
    """scene-keywords.json: scene_id -> [tags] → keyword -> {scene_id: weight}."""
    inverted: dict[str, dict[str, int]] = {}
    for scene_id, tags in raw.items():
        if not isinstance(tags, list):
            continue
        for tag in tags:
            kw = str(tag).strip().lower()
            if not kw:
                continue
            inverted.setdefault(kw, {})[scene_id] = max(inverted.get(kw, {}).get(scene_id, 0), 6)
    return inverted


def _merge_keyword_scores(
    js_scores: dict[str, dict[str, int]],
    file_scores: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    merged = {k: dict(v) for k, v in js_scores.items()}
    for kw, weights in file_scores.items():
        bucket = merged.setdefault(kw, {})
        for sid, wt in weights.items():
            bucket[sid] = max(bucket.get(sid, 0), wt)
    return merged


@lru_cache(maxsize=1)
def _load_registry() -> tuple[dict[str, str], dict[str, dict[str, int]], dict[str, str], dict[str, str]]:
    src = SCENE_IMAGES_JS.read_text(encoding="utf-8")
    scenes = _parse_js_map(re.search(r"const SCENES = \{([\s\S]*?)\};", src).group(1))
    kw_block = re.search(r"const KEYWORD_SCORES = \{([\s\S]*?)\};", src).group(1)
    keyword_scores = _parse_keyword_scores(kw_block)
    mood_defaults = _parse_js_map(re.search(r"const MOOD_DEFAULTS = \{([\s\S]*?)\};", src).group(1))
    style_defaults = _parse_js_map(re.search(r"const STYLE_DEFAULTS = \{([\s\S]*?)\};", src).group(1))
    style_defaults.update(STYLE_DEFAULTS)

    if SCENE_KEYWORDS.is_file():
        file_raw = json.loads(SCENE_KEYWORDS.read_text(encoding="utf-8"))
        keyword_scores = _merge_keyword_scores(keyword_scores, _invert_scene_keywords(file_raw))

    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for item in manifest.get("scenes") or []:
            sid = str(item.get("id") or "").strip()
            path = str(item.get("file") or "").strip()
            if sid and path:
                scenes[sid] = path
            for tag in item.get("tags") or []:
                kw = str(tag).strip().lower()
                if kw and sid:
                    keyword_scores.setdefault(kw, {})[sid] = max(keyword_scores.get(kw, {}).get(sid, 0), 7)

    if SCENES_DIR.is_dir():
        for png in SCENES_DIR.glob("*.png"):
            sid = png.stem
            if sid and sid not in scenes:
                scenes[sid] = f"images/scenes/{png.name}"

    return scenes, keyword_scores, mood_defaults, style_defaults


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff\s_-]", " ", text.lower())
    return [t for t in cleaned.split() if t]


def _extract_lines_text(lines: object) -> str:
    if not lines:
        return ""
    chunks: list[str] = []
    if isinstance(lines, list):
        for item in lines[:12]:
            if isinstance(item, dict):
                chunks.append(str(item.get("text") or ""))
            else:
                chunks.append(str(getattr(item, "text", "") or ""))
    return " ".join(c for c in chunks if c.strip())


def extract_story_context(
    *,
    setting: str = "",
    era: str = "",
    synopsis: str = "",
    tone: str = "",
    themes: object = None,
) -> tuple[str, str]:
    """Extract setting/era keywords from bible fields for every node match."""
    setting_parts: list[str] = []
    for chunk in (setting, synopsis, tone):
        text = str(chunk or "").strip()
        if text:
            setting_parts.append(text)
    if themes:
        if isinstance(themes, (list, tuple)):
            setting_parts.extend(str(t).strip() for t in themes if str(t).strip())
    combined = " ".join(setting_parts).strip()
    era_blob = str(era or "").strip()
    if not era_blob and combined:
        era_match = re.search(
            r"(十九世纪|18\d{2}|19th\s*century|维多利亚|民国|古代|唐朝|宋朝|明朝|清朝|仙侠|修仙|校园|大学)",
            combined,
            flags=re.IGNORECASE,
        )
        if era_match:
            era_blob = era_match.group(1)
    if combined:
        combined = f"{combined} {combined}"
    return combined, era_blob


def build_search_text(
    *,
    image_prompt: str = "",
    title: str = "",
    scene_type: str = "buildup",
    lines: object = None,
    setting: str = "",
    era: str = "",
    synopsis: str = "",
    style: str = "",
) -> str:
    """Assemble weighted search blob: title + prompt + dialogue + story setting."""
    parts: list[str] = []
    if (title or "").strip():
        parts.append(title.strip())
    if (image_prompt or "").strip():
        parts.append(image_prompt.strip())
    line_blob = _extract_lines_text(lines)
    if line_blob:
        parts.append(line_blob)
    for ctx in (setting, era, synopsis):
        text = str(ctx or "").strip()
        if text:
            parts.extend([text] * SETTING_CONTEXT_WEIGHT)
    has_user_text = bool(title.strip() or image_prompt.strip() or line_blob)
    has_story_context = bool(
        str(setting or "").strip() or str(era or "").strip() or str(synopsis or "").strip()
    )
    st = (scene_type or "buildup").lower()
    style_key = (style or "urban_romance").lower()
    hint = ""
    if style_key in STYLE_SCENE_TYPE_HINTS:
        hint = STYLE_SCENE_TYPE_HINTS[style_key].get(st, "")
    if not hint and has_user_text and not has_story_context and st in SCENE_TYPE_HINTS:
        hint = SCENE_TYPE_HINTS[st]
    if hint:
        parts.append(hint)
    return " ".join(parts).strip()


def _has_modern_context(text: str) -> bool:
    blob = text.lower()
    return any(cue in blob for cue in MODERN_CUES)


def _has_horror_context(text: str) -> bool:
    blob = text.lower()
    return any(cue in blob for cue in HORROR_CUES)


def _detect_period_fiction(text: str) -> bool:
    """True only for explicit 19th-c. / Maupassant-era fiction, not modern urban stories."""
    blob = text.lower()
    if not blob:
        return False
    if _has_modern_context(blob):
        return any(t in blob for t in TAG_TRIGGERS["19th_century"])
    if any(t in blob for t in TAG_TRIGGERS["19th_century"]):
        return True
    paris_cue = any(
        p in blob
        for p in (
            "paris street",
            "streets of paris",
            "paris boulevard",
            "paris at night",
            "塞纳河",
            "塞纳河畔",
            "seine river",
        )
    )
    if paris_cue and any(c in blob for c in PERIOD_SOFT_CUES):
        return True
    if ("巴黎" in blob or "塞纳" in blob) and any(c in blob for c in PERIOD_SOFT_CUES):
        return True
    cluster_hits = sum(
        1
        for tag in PERIOD_CLUSTER_TAGS
        if any(phrase in blob for phrase in TAG_TRIGGERS[tag])
    )
    if cluster_hits >= 2:
        return True
    if any(m in blob for m in MODEST_PERIOD_PHRASES) and cluster_hits >= 1:
        return True
    return False


INTERIOR_CUES: tuple[str, ...] = (
    "apartment",
    "flat",
    "room",
    "interior",
    "home",
    "house",
    "kitchen",
    "bedroom",
    "公寓",
    "房间",
    "寒舍",
    "陋室",
    "客厅",
    "卧室",
    "家里",
    "屋内",
    "出租",
)


def _interior_context(text: str) -> bool:
    blob = text.lower()
    return any(cue in blob for cue in INTERIOR_CUES)


def _paris_street_scene_ids() -> frozenset[str]:
    return frozenset(SCENE_TAG_WEIGHTS.get("paris_street", {}).keys())


def _score_from_tags(text: str, *, style_key: str = "", period_fiction: bool = False) -> dict[str, int]:
    scores: dict[str, int] = {}
    blob = text.lower()
    interior = _interior_context(text)
    paris_street_ids = _paris_street_scene_ids()
    horror = _has_horror_context(blob)
    for tag, phrases in TAG_TRIGGERS.items():
        if not any(p in blob for p in phrases):
            continue
        if tag == "paris_street":
            if interior or (not period_fiction and not any(p in blob for p in ("巴黎", "paris", "塞纳", "seine"))):
                continue
        if tag == "mirror_room" and horror and style_key in {"mystery", "horror"}:
            for sid, wt in {
                "haunted_mansion_stair": 10,
                "ghost_mansion": 8,
                "haunted_toilet_crack": 7,
                "apartment_bedroom": 5,
            }.items():
                scores[sid] = scores.get(sid, 0) + wt
            continue
        for sid, wt in SCENE_TAG_WEIGHTS.get(tag, {}).items():
            if interior and tag == "19th_century" and sid in paris_street_ids:
                continue
            scores[sid] = scores.get(sid, 0) + wt
    return scores


def _apply_scene_aliases(scores: dict[str, int]) -> dict[str, int]:
    merged = dict(scores)
    for alias_id, target_id in SCENE_ALIASES.items():
        if alias_id not in merged:
            continue
        merged[target_id] = merged.get(target_id, 0) + merged.pop(alias_id)
    return merged


def _resolve_alias(scene_id: str) -> str:
    return SCENE_ALIASES.get(scene_id, scene_id)


def _score_from_text(
    text: str,
    keyword_scores: dict[str, dict[str, int]],
    *,
    style_key: str = "",
    period_fiction: bool = False,
) -> dict[str, int]:
    scores: dict[str, int] = {}
    tokens = _tokenize(text)
    blob = " ".join(tokens)
    interior = _interior_context(text)
    paris_street_ids = _paris_street_scene_ids()
    paris_location_kw = frozenset({"paris", "巴黎", "欧洲", "europe"})
    for keyword in sorted(keyword_scores.keys(), key=len, reverse=True):
        if keyword not in blob:
            continue
        if not period_fiction and keyword in PERIOD_LOCATION_KEYWORDS:
            continue
        for scene_id, weight in keyword_scores[keyword].items():
            if interior and keyword in paris_location_kw and scene_id in paris_street_ids:
                continue
            if not period_fiction and scene_id in EUROPEAN_PERIOD_SCENES:
                continue
            scores[scene_id] = scores.get(scene_id, 0) + weight
    for token in tokens:
        weights = keyword_scores.get(token)
        if not weights:
            continue
        if not period_fiction and token in PERIOD_LOCATION_KEYWORDS:
            continue
        for scene_id, weight in weights.items():
            if not period_fiction and scene_id in EUROPEAN_PERIOD_SCENES:
                continue
            scores[scene_id] = scores.get(scene_id, 0) + int(weight * 1.5)
    tag_scores = _score_from_tags(text, style_key=style_key, period_fiction=period_fiction)
    for sid, wt in tag_scores.items():
        scores[sid] = scores.get(sid, 0) + wt
    return _apply_scene_aliases(scores)


def _effective_style(style: str, search_text: str) -> str:
    style_key = (style or "urban_romance").lower()
    if style_key == "period_fiction":
        return style_key
    if _detect_period_fiction(search_text):
        return "period_fiction"
    return style_key


def _pool_pick(style: str, mood: str, node_id: str, scenes: dict[str, str]) -> str:
    pool = [sid for sid in STYLE_POOLS.get(style, STYLE_POOLS["urban_romance"]) if sid in scenes]
    if not pool:
        pool = list(scenes.keys())
    mood_default = (_load_registry()[2].get(mood) or "").strip()
    if mood_default and mood_default in pool:
        pool = [mood_default] + [s for s in pool if s != mood_default]
    digest = hashlib.md5(f"{style}:{node_id}".encode()).hexdigest()
    idx = int(digest[:8], 16) % len(pool)
    return pool[idx]


def _pick_best_scene(
    scores: dict[str, int],
    *,
    scenes: dict[str, str],
    mood_key: str,
    style_key: str,
    node_id: str,
    mood_defaults: dict[str, str],
    style_defaults: dict[str, str],
    avoid_paths: set[str],
    period_fiction: bool,
) -> tuple[str, float]:
    mood_default = mood_defaults.get(mood_key)
    style_default = style_defaults.get(style_key)
    best_id: str | None = None
    best_score = -1.0
    ranked: list[tuple[str, float]] = []

    for sid, base in scores.items():
        if sid not in scenes:
            continue
        s = float(base)
        if mood_default == sid:
            s += 2.0
        if style_default == sid:
            s += 1.5
        if period_fiction and sid in GENERIC_URBAN_SCENES:
            s -= PERIOD_FICTION_PENALTY
        if style_key in NON_URBAN_STYLES and sid in GENERIC_URBAN_SCENES:
            s -= PERIOD_FICTION_PENALTY
        if not period_fiction and sid in EUROPEAN_PERIOD_SCENES:
            s -= EUROPEAN_PERIOD_PENALTY
        path = _clean_path(scenes.get(sid) or "")
        if path and path in avoid_paths:
            s -= REPEAT_BG_PENALTY
        ranked.append((sid, s))
        if s > best_score:
            best_score = s
            best_id = sid

    if not ranked:
        fallback = mood_default or style_default or "calm_meadow"
        return fallback, 0.0

    ranked.sort(key=lambda x: x[1], reverse=True)
    scene_id = best_id or ranked[0][0]
    top_score = ranked[0][1]

    if node_id and len(ranked) > 1:
        tied = [sid for sid, sc in ranked if sc >= top_score - 0.5]
        if len(tied) > 1:
            digest = hashlib.md5(f"{style_key}:{node_id}".encode()).hexdigest()
            scene_id = tied[int(digest[:8], 16) % len(tied)]
        elif scene_id in (style_default, mood_default):
            alt = next((sid for sid, _ in ranked if sid != scene_id), None)
            if alt:
                scene_id = alt

    return scene_id, best_score


def resolve_scene(
    *,
    mood: str = "neutral",
    style: str = "urban_romance",
    image_prompt: str = "",
    title: str = "",
    scene_type: str = "buildup",
    node_id: str = "",
    lines: object = None,
    setting: str = "",
    era: str = "",
    synopsis: str = "",
    avoid_paths: frozenset[str] | set[str] | None = None,
) -> tuple[str, str, str]:
    """Return (scene_id, bg_path, match_reason). bg_path is manifest-relative."""
    scenes, keyword_scores, mood_defaults, style_defaults = _load_registry()
    mood_key = (mood or "neutral").lower()
    style_raw = (style or "urban_romance").lower()
    search_text = build_search_text(
        image_prompt=image_prompt,
        title=title,
        scene_type=scene_type,
        lines=lines,
        setting=setting,
        era=era,
        synopsis=synopsis,
        style=style_raw,
    )
    style_key = _effective_style(style, search_text)
    period_fiction = style_key == "period_fiction"
    avoid = set(avoid_paths or ())

    # Title and dialogue get extra weight on top of the combined search blob.
    line_blob = _extract_lines_text(lines)
    title_blob = (title or "").strip()
    score_kw = {
        "style_key": style_key,
        "period_fiction": period_fiction,
    }
    scores = _score_from_text(search_text, keyword_scores, **score_kw)
    if title_blob:
        title_scores = _score_from_text(title_blob, keyword_scores, **score_kw)
        for sid, wt in title_scores.items():
            scores[sid] = scores.get(sid, 0) + int(wt * TITLE_TEXT_WEIGHT)
    if line_blob:
        line_scores = _score_from_text(line_blob, keyword_scores, **score_kw)
        for sid, wt in line_scores.items():
            scores[sid] = scores.get(sid, 0) + int(wt * LINES_TEXT_WEIGHT)

    if not scores:
        story_text = build_search_text(
            setting=setting,
            era=era,
            synopsis=synopsis,
            scene_type=scene_type,
            style=style_key,
        )
        if story_text.strip():
            scores = _score_from_text(story_text, keyword_scores, **score_kw)

    if not scores:
        if node_id:
            fallback_id = _pool_pick(style_key, mood_key, node_id, scenes)
            reason = f"pool:{style_key}:{node_id}"
        else:
            fallback_id = (
                mood_defaults.get(mood_key)
                or style_defaults.get(style_key)
                or _pool_pick(style_key, mood_key, node_id or title or image_prompt, scenes)
            )
            reason = f"default:{fallback_id}"
        path = _clean_path(
            scenes.get(fallback_id) or scenes.get("calm_meadow") or next(iter(scenes.values()), "")
        )
        if path in avoid:
            for alt_id in STYLE_POOLS.get(style_key, STYLE_POOLS["urban_romance"]):
                alt_path = _clean_path(scenes.get(alt_id) or "")
                if alt_path and alt_path not in avoid:
                    return _resolve_alias(alt_id), alt_path, f"pool_avoid:{alt_id}"
        return _resolve_alias(fallback_id), path, reason

    scene_id, best_score = _pick_best_scene(
        scores,
        scenes=scenes,
        mood_key=mood_key,
        style_key=style_key,
        node_id=node_id,
        mood_defaults=mood_defaults,
        style_defaults=style_defaults,
        avoid_paths=avoid,
        period_fiction=period_fiction,
    )
    scene_id = _resolve_alias(scene_id)
    reason = f"keyword:{scene_id}:{best_score:.1f}"

    path = _clean_path(scenes.get(scene_id) or scenes.get("calm_meadow") or next(iter(scenes.values()), ""))
    if path in avoid:
        ranked = sorted(
            ((sid, sc) for sid, sc in scores.items() if sid in scenes),
            key=lambda x: x[1],
            reverse=True,
        )
        for alt_id, alt_sc in ranked:
            alt_path = _clean_path(scenes.get(alt_id) or "")
            if alt_path and alt_path not in avoid:
                return _resolve_alias(alt_id), alt_path, f"keyword_avoid:{alt_id}:{alt_sc:.1f}"
    return scene_id, path, reason


def assign_node_backgrounds(
    nodes: Mapping[str, object],
    style: str,
    *,
    setting: str = "",
    era: str = "",
    synopsis: str = "",
    tone: str = "",
    themes: object = None,
) -> None:
    """Mutate node-like dicts or StoryNode models in place with scene_id + bg_path."""
    setting_blob, era_blob = extract_story_context(
        setting=setting,
        era=era,
        synopsis=synopsis,
        tone=tone,
        themes=themes,
    )
    used_paths: set[str] = set()
    last_bg_path: str | None = None

    for nid, node in nodes.items():
        if isinstance(node, dict):
            getter = node.get
            setter = node.__setitem__
        else:
            getter = lambda k, d="", _n=node: getattr(_n, k, d)
            setter = lambda k, v, _n=node: setattr(_n, k, v)

        if getter("bg_path"):
            existing = str(getter("bg_path"))
            used_paths.add(existing)
            last_bg_path = existing
            continue

        avoid: set[str] = set()
        if last_bg_path:
            avoid.add(last_bg_path)

        scene_id, bg_path, match_reason = resolve_scene(
            mood=str(getter("mood") or "neutral"),
            style=style,
            image_prompt=str(getter("image_prompt") or ""),
            title=str(getter("title") or ""),
            scene_type=str(getter("scene_type") or "buildup"),
            node_id=str(getter("id") or nid),
            lines=getter("lines"),
            setting=setting_blob,
            era=era_blob,
            synopsis=synopsis,
            avoid_paths=avoid,
        )

        if bg_path in used_paths:
            scenes, _, _, _ = _load_registry()
            style_key = _effective_style(
                style,
                build_search_text(
                    image_prompt=str(getter("image_prompt") or ""),
                    title=str(getter("title") or ""),
                    lines=getter("lines"),
                    setting=setting_blob,
                    era=era_blob,
                    synopsis=synopsis,
                    style=style,
                ),
            )
            pool = STYLE_POOLS.get(style_key, STYLE_POOLS["urban_romance"])
            for alt_id in pool:
                alt_path = _clean_path(scenes.get(alt_id, ""))
                if alt_path and alt_path not in used_paths and alt_path != last_bg_path:
                    scene_id, bg_path = alt_id, alt_path
                    match_reason = f"dedup_pool:{alt_id}"
                    break

        setter("scene_id", scene_id)
        setter("bg_path", bg_path)
        try:
            setter("scene_match_reason", match_reason)
        except Exception:
            pass
        used_paths.add(bg_path)
        last_bg_path = bg_path
