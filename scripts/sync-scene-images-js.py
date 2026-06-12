#!/usr/bin/env python3
"""Regenerate scene-images.js SCENES map — PNG only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "frontend" / "images" / "scenes"
OUT_JS = ROOT / "frontend" / "js" / "scene-images.js"
MANIFEST = ROOT / "frontend" / "images" / "manifest.json"
SCRIPTS = Path(__file__).resolve().parent

PROMPTS = SCRIPTS / "scene-prompts.json"
KEYWORDS_JSON = SCRIPTS / "scene-keywords.json"

prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
ids = sorted(prompts.keys())
png_ids = {p.stem for p in SCENES_DIR.glob("*.png")}
version = 15

BASE_KEYWORDS: dict[str, dict[str, int]] = {
    "meadow": {"calm_meadow": 4, "campus_field": 2, "flower_field": 3, "meadow_windmill": 3},
    "calm": {"calm_meadow": 3, "lakeside_dock": 2},
    "peaceful": {"calm_meadow": 3, "indoor_warm": 2, "tea_house": 2},
    "grassland": {"calm_meadow": 3, "windy_hill": 2},
    "sunset": {"sunset_hill": 4, "rooftop_sky": 2, "beach_wind": 2, "airport_sunset": 3, "harbor_dawn": 2},
    "dawn": {"sunset_hill": 3, "harbor_dawn": 4, "calm_meadow": 2},
    "golden": {"sunset_hill": 2, "village_dusk": 3},
    "hill": {"sunset_hill": 3, "windy_hill": 3, "mystery_fog": 1},
    "forest": {"forest_path": 5, "enchanted_grove": 4, "bamboo_grove": 4, "cherry_tunnel": 3},
    "woods": {"forest_path": 4, "bamboo_grove": 3},
    "tree": {"forest_path": 3, "winter_snow": 1, "cherry_tunnel": 3},
    "path": {"forest_path": 3, "shrine_path": 3, "rainy_street": 1},
    "rain": {"rainy_street": 5, "bamboo_rain": 4, "storm_coast": 2, "hallway_rainstorm": 4},
    "rainy": {"rainy_street": 5, "bamboo_rain": 4, "hallway_rainstorm": 4},
    "wet": {"rainy_street": 3, "market_alley": 1, "wet_market_haggle": 5},
    "street": {"rainy_street": 4, "city_lights": 2, "market_alley": 3},
    "school": {"school_corridor": 4, "campus_field": 3, "rooftop_sky": 2, "classroom_drowse": 4},
    "classroom": {"school_corridor": 3, "library_aisle": 2, "classroom_drowse": 5},
    "corridor": {"school_corridor": 5, "hospital_hall": 2},
    "campus": {"campus_field": 4, "school_corridor": 2},
    "field": {"campus_field": 4, "flower_field": 3},
    "rooftop": {"rooftop_sky": 5, "balcony_night": 3, "rooftop_secret": 5},
    "roof": {"rooftop_sky": 4, "rooftop_secret": 4},
    "sky": {"rooftop_sky": 2, "night_stars": 2, "castle_clouds": 3, "sky_tram": 4},
    "night": {"night_stars": 4, "city_lights": 3, "lantern_festival": 4, "night_bazaar": 3},
    "star": {"night_stars": 5, "observatory": 4},
    "stars": {"night_stars": 5, "observatory": 3},
    "moon": {"night_stars": 4, "moon_bridge": 5},
    "city": {"city_lights": 4, "rainy_street": 2, "clock_tower": 3, "subway_night": 3},
    "urban": {"city_lights": 3, "market_alley": 3},
    "neon": {"city_lights": 3, "subway_night": 2, "cyberpunk_alley_gun": 4, "cyber_city_rain": 4},
    "lights": {"city_lights": 3, "lantern_festival": 3},
    "fog": {"mystery_fog": 5, "ghost_mansion": 4, "pagoda_mist": 3},
    "mist": {"mystery_fog": 4, "pagoda_mist": 4, "hot_spring": 2, "hot_spring_mist": 5},
    "mystery": {"mystery_fog": 4, "ghost_mansion": 3},
    "cafe": {"romance_cafe": 5, "tea_house": 3},
    "coffee": {"romance_cafe": 4},
    "romance": {"romance_cafe": 4, "sunset_hill": 2, "sakura_river": 3},
    "romantic": {"romance_cafe": 3, "sunset_hill": 3, "cherry_tunnel": 3},
    "mountain": {"xianxia_peaks": 4, "pagoda_mist": 3, "rice_terraces": 4},
    "peak": {"xianxia_peaks": 4, "volcano_dusk": 2, "tribulation_peak": 5},
    "peaks": {"xianxia_peaks": 4},
    "xianxia": {"xianxia_peaks": 5, "pagoda_mist": 3, "shrine_path": 2, "sect_arena": 4},
    "indoor": {"indoor_warm": 4, "library_aisle": 3, "tea_house": 3},
    "room": {"indoor_warm": 3, "candle_room": 4},
    "warm": {"indoor_warm": 3, "hot_spring": 2},
    "home": {"indoor_warm": 3, "balcony_night": 2},
    "beach": {"beach_wind": 5, "cliff_lighthouse": 3, "storm_coast": 2},
    "ocean": {"beach_wind": 4, "storm_coast": 3, "harbor_dawn": 2},
    "sea": {"beach_wind": 3, "storm_coast": 3, "crystal_spring": 2},
    "coast": {"beach_wind": 4, "cliff_lighthouse": 4},
    "wind": {"beach_wind": 3, "windy_hill": 4, "train_countryside": 1},
    "train": {"train_countryside": 5, "sky_tram": 3},
    "railway": {"train_countryside": 4},
    "countryside": {"train_countryside": 4, "village_dusk": 3},
    "snow": {"winter_snow": 5, "snow_shrine": 5, "plum_garden_snow": 4},
    "winter": {"winter_snow": 5, "snow_shrine": 4},
    "cold": {"winter_snow": 3, "snow_shrine": 3},
    "shrine": {"shrine_path": 5, "snow_shrine": 4},
    "temple": {"snow_shrine": 4, "pagoda_mist": 3, "temple_ruins_array": 4},
    "lake": {"lakeside_dock": 5, "moon_bridge": 3, "crystal_spring": 3},
    "river": {"sakura_river": 5, "canal_twilight": 4},
    "bridge": {"moon_bridge": 5, "canal_twilight": 2, "nether_bridge": 4},
    "spring": {"hot_spring": 4, "crystal_spring": 4},
    "castle": {"castle_clouds": 5, "ruins_vine": 3},
    "floating": {"floating_isles": 5, "castle_clouds": 3},
    "desert": {"desert_oasis": 5},
    "oasis": {"desert_oasis": 5},
    "volcano": {"volcano_dusk": 5},
    "cave": {"cave_glow": 5, "dragon_nest_egg": 4},
    "waterfall": {"waterfall_rainbow": 5},
    "greenhouse": {"greenhouse": 5, "mars_greenhouse_patch": 4},
    "hospital": {"hospital_hall": 5, "hospital_blood_elevator": 4, "er_waiting_room": 5},
    "library": {"library_aisle": 5, "library_window_nap": 5, "library_sweeping_monk": 4},
    "airport": {"airport_sunset": 5},
    "subway": {"subway_night": 5, "crowded_subway": 5},
    "market": {"night_bazaar": 4, "market_alley": 5, "wet_market_haggle": 4},
    "camp": {"campsite": 5},
    "autumn": {"autumn_road": 5},
    "cherry": {"cherry_tunnel": 5, "sakura_river": 4},
    "sakura": {"sakura_river": 5, "cherry_tunnel": 4},
    "bamboo": {"bamboo_grove": 5, "bamboo_rain": 4},
    "storm": {"thunder_field": 4, "storm_coast": 4, "storm_no_ride": 4},
    "thunder": {"thunder_field": 5, "tribulation_peak": 4},
    "lighthouse": {"cliff_lighthouse": 5},
    "windmill": {"meadow_windmill": 5},
    "rice": {"rice_terraces": 5},
    "clock": {"clock_tower": 5},
    "ghost": {"ghost_mansion": 5, "ghost_wedding_hall": 5, "paper_doll_village": 4},
    "lantern": {"lantern_festival": 5, "rabbit_lantern_fair": 5},
    "tram": {"sky_tram": 5},
    "observatory": {"observatory": 5},
    "cliff": {"cliff_lighthouse": 3, "beach_wind": 2, "cliff_leap": 5},
    "club": {"campus_field": 2, "school_corridor": 1},
    "fair": {"campus_field": 3, "night_bazaar": 2, "rabbit_lantern_fair": 4},
    "office": {"office_midnight": 5, "tense_meeting": 4},
    "elevator": {"ceo_elevator": 5, "hospital_blood_elevator": 4},
    "wedding": {"wedding_room_alone": 5, "wedding_banquet_hall": 6, "ghost_wedding_hall": 4},
    "funeral": {"funeral_hall_empty": 6},
    "hometown": {"old_hometown_street": 6, "grandparents_yard": 5},
    "farewell": {"train_farewell_platform": 6, "airport_sunset": 3},
    "grandparent": {"grandparents_yard": 6},
    "candle": {"candlelit_room": 6, "candle_room": 4},
    "confession": {"balcony_confession_night": 6, "rooftop_secret": 4},
    "prison": {"prison_cell_taunt": 5},
    "dragon": {"dragon_nest_egg": 5},
    "mech": {"mech_hangar_weld": 5, "colosseum_cyber_arm": 4},
    "zombie": {"supermarket_siege": 5},
    "mars": {"mars_greenhouse_patch": 5, "mars_base_dome": 5},
    "throne": {"throne_hall_debate": 5},
    "execution": {"execution_scaffold": 5},
}


def merge_zh_keywords(scores: dict[str, dict[str, int]]) -> None:
    if not KEYWORDS_JSON.is_file():
        return
    zh = json.loads(KEYWORDS_JSON.read_text(encoding="utf-8"))
    for sid, words in zh.items():
        for w in words:
            if w not in scores:
                scores[w] = {}
            scores[w][sid] = max(scores[w].get(sid, 0), 6)


def format_keyword_scores(scores: dict[str, dict[str, int]]) -> str:
    lines = ["  /** 关键词 → 场景 id，值越大越优先 */", "  const KEYWORD_SCORES = {"]
    for kw in sorted(scores.keys()):
        inner = ", ".join(f"{sid}: {n}" for sid, n in sorted(scores[kw].items()))
        lines.append(f"    {json.dumps(kw, ensure_ascii=False)}: {{ {inner} }},")
    lines.append("  };")
    return "\n".join(lines)


scores = dict(BASE_KEYWORDS)
merge_zh_keywords(scores)
keyword_block = format_keyword_scores(scores)

lines = [
    "/** 场景图库 — mood / style / image_prompt 关键词 → 最佳背景图 */",
    "const SceneImages = (function () {",
    f"  const VERSION = {version};",
    "",
    "  const SCENES = {",
]
for sid in ids:
    if sid not in png_ids:
        print(f"WARN: missing PNG for {sid}")
    lines.append(f'    {sid}: "images/scenes/{sid}.png?v=" + VERSION,')
lines.append("  };")
lines.append("")
lines.append(keyword_block)

TAIL = r'''

  const MOOD_DEFAULTS = {
    calm: "calm_meadow",
    tense: "rainy_street",
    romantic: "sunset_hill",
    romance: "romance_cafe",
    mysterious: "mystery_fog",
    mystery: "mystery_fog",
    neutral: "calm_meadow",
    sad: "rainy_street",
    hopeful: "sunset_hill",
    dark_mystery: "mystery_fog",
    neon_rain: "rainy_street",
    golden_dawn: "sunset_hill",
    storm_sea: "beach_wind",
  };

  const STYLE_DEFAULTS = {
    xianxia: "xianxia_peaks",
    urban_romance: "city_lights",
    mystery: "mystery_fog",
    campus: "campus_field",
  };

  const MOOD_VEIL = {
    dark_mystery: "linear-gradient(180deg, rgba(42,56,72,0.35) 0%, rgba(58,72,88,0.25) 100%)",
    neon_rain: "linear-gradient(180deg, rgba(126,184,255,0.12) 0%, rgba(248,168,200,0.08) 100%)",
    golden_dawn: "linear-gradient(180deg, rgba(255,200,221,0.1) 0%, rgba(168,212,255,0.08) 100%)",
    storm_sea: "linear-gradient(180deg, rgba(74,88,104,0.28) 0%, rgba(58,64,88,0.2) 100%)",
    neutral: "linear-gradient(180deg, rgba(250,246,237,0.08) 0%, rgba(58,72,58,0.14) 100%)",
    calm: "linear-gradient(180deg, rgba(250,246,237,0.08) 0%, rgba(107,142,107,0.1) 100%)",
    tense: "linear-gradient(180deg, rgba(74,88,104,0.22) 0%, rgba(58,64,88,0.18) 100%)",
    romantic: "linear-gradient(180deg, rgba(255,200,221,0.12) 0%, rgba(168,212,255,0.06) 100%)",
    mysterious: "linear-gradient(180deg, rgba(42,56,72,0.3) 0%, rgba(74,104,80,0.15) 100%)",
    sad: "linear-gradient(180deg, rgba(74,88,104,0.25) 0%, rgba(58,64,88,0.2) 100%)",
    hopeful: "linear-gradient(180deg, rgba(255,200,221,0.1) 0%, rgba(168,212,255,0.1) 100%)",
  };

  const imageCache = {};
  let imageGenEnabled = false;

  function preload() {
    Object.keys(SCENES).forEach(function (id) {
      const img = new Image();
      img.src = SCENES[id];
      imageCache[id] = img;
    });
  }

  function tokenize(text) {
    if (!text) return [];
    return text
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fff\s_-]/g, " ")
      .split(/\s+/)
      .filter(Boolean);
  }

  function scoreFromPrompt(prompt) {
    const scores = {};
    const tokens = tokenize(prompt);
    const blob = tokens.join(" ");

    Object.keys(KEYWORD_SCORES).forEach(function (keyword) {
      if (blob.indexOf(keyword) === -1) return;
      const weights = KEYWORD_SCORES[keyword];
      Object.keys(weights).forEach(function (sceneId) {
        scores[sceneId] = (scores[sceneId] || 0) + weights[sceneId];
      });
    });

    tokens.forEach(function (token) {
      if (KEYWORD_SCORES[token]) {
        const weights = KEYWORD_SCORES[token];
        Object.keys(weights).forEach(function (sceneId) {
          scores[sceneId] = (scores[sceneId] || 0) + weights[sceneId] * 1.5;
        });
      }
    });

    return scores;
  }

  function resolve(mood, style, imagePrompt) {
    const moodKey = (mood || "neutral").toLowerCase();
    const scores = scoreFromPrompt(imagePrompt || "");

    if (Object.keys(scores).length === 0) {
      const fallback =
        MOOD_DEFAULTS[moodKey] ||
        STYLE_DEFAULTS[style] ||
        "calm_meadow";
      return {
        sceneId: fallback,
        path: SCENES[fallback] || SCENES.calm_meadow,
        veil: MOOD_VEIL[moodKey] || MOOD_VEIL.neutral,
        mood: moodKey,
      };
    }

    let bestId = null;
    let bestScore = -1;
    Object.keys(scores).forEach(function (id) {
      if (!SCENES[id]) return;
      let s = scores[id];
      if (MOOD_DEFAULTS[moodKey] === id) s += 2;
      if (STYLE_DEFAULTS[style] === id) s += 1.5;
      if (s > bestScore) {
        bestScore = s;
        bestId = id;
      }
    });

    const sceneId = bestId || MOOD_DEFAULTS[moodKey] || STYLE_DEFAULTS[style] || "calm_meadow";
    return {
      sceneId: sceneId,
      path: SCENES[sceneId] || SCENES.calm_meadow,
      veil: MOOD_VEIL[moodKey] || MOOD_VEIL.neutral,
      mood: moodKey,
    };
  }

  function setImageGenEnabled(enabled) {
    imageGenEnabled = !!enabled;
  }

  function isImageGenEnabled() {
    return imageGenEnabled;
  }

  async function fetchAiSceneImage(prompt, mood) {
    if (!imageGenEnabled || !prompt) return null;
    try {
      const res = await fetch("/api/scene-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt, mood: mood || "neutral" }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.url || null;
    } catch (_) {
      return null;
    }
  }

  async function probeImageGen() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) return;
      const data = await res.json();
      setImageGenEnabled(!!data.image_gen);
    } catch (_) {
      setImageGenEnabled(false);
    }
  }

  preload();
  probeImageGen();

  return {
    SCENES,
    resolve,
    fetchAiSceneImage,
    setImageGenEnabled,
    isImageGenEnabled,
    probeImageGen,
  };
})();
'''

content = "\n".join(lines) + TAIL
OUT_JS.write_text(content, encoding="utf-8")

ui_manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
ui = ui_manifest.get("ui", [])
manifest = {
    "ui": ui,
    "scenes": [{"id": sid, "file": f"images/scenes/{sid}.png"} for sid in ids],
    "count": len(ids),
    "version": version,
    "art_style": "scripts/art-style.json",
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Updated {OUT_JS.name} with {len(ids)} scenes (v{version})")
