# Scene-to-Story Matching Audit

**Date:** 2026-06-09  
**Files:** `frontend/js/scene-images.js` (v16), `frontend/js/mood.js`, `backend/prompts.py`, `backend/image_service.py`  
**Coordination:** pure-background-only regen rule (no protagonist / VN UI in scene PNGs)

## How matching works

1. LLM emits per-node `image_prompt` (English, 15–40 words) in `backend/prompts.py`.
2. `MoodBackgrounds.apply()` (`mood.js`) calls `SceneImages.resolve(mood, style, imagePrompt)`.
3. `scoreFromPrompt()` tokenizes the prompt, scans `KEYWORD_SCORES` (longest keyword first), sums weights per scene id, then adds mood/style default bonuses (+2 / +1.5).
4. Winner’s PNG is loaded with mood veil gradient; on `onerror` falls back to CSS gradient only.

`image_service.py` already enforces: *no text, no watermark, no characters* for AI-generated fallbacks.

## Sample phrase results (after fixes)

| Phrase | Style / Mood | Winner | Notes |
|--------|--------------|--------|-------|
| 食堂吃饭 | campus / neutral | `cafeteria_serving` | Was `family_dining` (吃饭 alone) |
| school cafeteria lunch | campus / neutral | `cafeteria_serving` | Added EN `cafeteria`/`lunch` |
| 皇宫大殿 | xianxia / neutral | `imperial_palace_hall` | Was mood fallback |
| imperial palace throne hall | xianxia / golden_dawn | `throne_hall_debate` | EN `palace` + `throne` |
| 太平间 | mystery / dark_mystery | `morgue_corridor_blue` | Was mood fallback |
| morgue corridor | mystery / dark_mystery | `morgue_corridor_blue` | Was `school_corridor` |
| 考场 / exam hall silent | campus / tense | `exam_hall_silent` | EN `exam` added |
| 客栈 / ancient inn courtyard rain | xianxia | `jianghu_inn` / `ancient_inn_courtyard` | `inn`/`ancient` EN + 烟雨 |
| 都市夜景霓虹 | urban_romance / neon_rain | `city_lights` | Removed broad `夜`; added 都市夜景 |
| 校园操场 | campus / hopeful | `sunny_basketball` | Added 校园 |
| 悬疑案发现场 | mystery | `crime_tape_alley` | OK (existing 案发现场) |

Re-run: `node scripts/audit-scene-matching.mjs`

## Genre coverage

| Genre | Status | Gaps addressed |
|-------|--------|----------------|
| **古代** | Improved | 皇宫/大殿/金銮殿 → `imperial_palace_*`, `throne_hall_debate`; 客栈 → `jianghu_inn` / `ancient_inn_courtyard` |
| **悬疑** | Improved | 太平间 → `morgue_corridor_blue`; EN `morgue`; `mystery` → `crime_tape_alley` |
| **校园** | Improved | 食堂吃饭, EN cafeteria/exam; 校园 → campus scenes |
| **都市** | Improved | 都市/都市夜景/夜景 → `city_lights`, `cyber_city_rain`; removed single-char `夜` hijack |

**Remaining risk:** LLM `image_prompt` is English — Chinese node `title` alone does not score; prompts must include location nouns (cafeteria, palace, morgue, inn, campus field, etc.). `prompts.py` now states empty background + location keywords.

## Fixes applied (scene-images.js v15 → v16)

### SCENES registry
- Added PNG entries: `gas_station_night`, `law_firm_office`, `taxi_interior_night`, `tv_studio_live`, `morgue_corridor_blue`, `imperial_palace_throne`.
- `sunset_duty` interim path → `classroom_drowse.png` (asset not generated yet).

### KEYWORD_SCORES
- EN: `cafeteria`, `exam`, `morgue`, `inn`, `palace`, `ancient`, `dining`, `lunch`.
- ZH: 皇宫, 大殿, 太平间, 食堂吃饭, 古代客栈, 校园, 都市, 都市夜景; boosted 夜景/城市夜景.
- Reduced `吃饭` weight; removed standalone `夜` (substring false positives).
- `corridor` rebalanced; longest-keyword-first sort in `scoreFromPrompt`.

### Broken refs fixed
Previously keyword-targeted ids with **no SCENES entry** (scores silently dropped): `gas_station_night`, `law_firm_office`, `taxi_interior_night`, `tv_studio_live`.

## PNG inventory

- **253** ids in `SCENES`; **359** PNGs on disk (112 orphan assets not wired — future expansion).
- All `SCENES` paths resolve to existing files except logical id `sunset_duty` (uses `classroom_drowse` placeholder).

## Regen list — UI overlay / protagonist risk

Per `scripts/build-scene-library.py` narrative briefs (pre–pure-background rule). Prefer empty environment regen:

| Priority | Scene id | Issue |
|----------|----------|-------|
| High | `classroom_drowse`, `snack_shop_rush`, `sunset_duty` | Students / protagonist actions in brief |
| High | `storm_no_ride`, `wet_market_haggle`, `charity_gala` | Explicit protagonist in prompt |
| High | `hall_disciple_fight`, `mist_beast_forest`, `tomb_wall_script` | Characters / hiding protagonist |
| High | `jianghu_inn`, `cliff_leap`, `nether_bridge`, `dragon_nest_egg` | Plot-locked figures |
| Medium | `ceo_elevator`, `blind_date_restaurant`, `cursed_bus_ride` | Close-up POV / faces |
| Medium | `cafeteria_serving`, `crowded_subway`, `office_midnight` | Crowd silhouettes OK if no hero |

**Already aligned:** `image_service.py` + updated LLM `image_prompt` spec (empty background, location keywords).

## mood.js notes

- Dual-layer crossfade (`#scene-bg-a/b`), veil + `url(scene.png)`, mood filter.
- No changes required; matching is entirely in `SceneImages.resolve`.
