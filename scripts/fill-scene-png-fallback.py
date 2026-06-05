#!/usr/bin/env python3
"""Copy best available AI PNG archetype for scenes still missing PNG."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENES = ROOT / "frontend" / "images" / "scenes"
PROMPTS = Path(__file__).resolve().parent / "scene-prompts.json"
ARCHETYPES_JSON = Path(__file__).resolve().parent / "scene-archetypes.json"

# scene_id -> existing png archetype (must exist on disk)
ARCHETYPE: dict[str, str] = {
    "bamboo_grove": "forest_path",
    "bamboo_rain": "forest_path",
    "enchanted_grove": "forest_path",
    "cherry_tunnel": "forest_path",
    "autumn_road": "forest_path",
    "shrine_path": "forest_path",
    "snow_shrine": "winter_snow",
    "pagoda_mist": "xianxia_peaks",
    "rice_terraces": "xianxia_peaks",
    "floating_isles": "xianxia_peaks",
    "castle_clouds": "xianxia_peaks",
    "sky_tram": "xianxia_peaks",
    "volcano_dusk": "xianxia_peaks",
    "flower_field": "calm_meadow",
    "meadow_windmill": "calm_meadow",
    "windy_hill": "calm_meadow",
    "village_dusk": "sunset_hill",
    "harbor_dawn": "beach_wind",
    "cliff_lighthouse": "beach_wind",
    "storm_coast": "beach_wind",
    "crystal_spring": "beach_wind",
    "waterfall_rainbow": "beach_wind",
    "canal_twilight": "rainy_street",
    "market_alley": "rainy_street",
    "subway_night": "city_lights",
    "clock_tower": "city_lights",
    "balcony_night": "city_lights",
    "night_bazaar": "city_lights",
    "lantern_festival": "city_lights",
    "moon_bridge": "night_stars",
    "observatory": "night_stars",
    "campsite": "night_stars",
    "ghost_mansion": "mystery_fog",
    "cave_glow": "mystery_fog",
    "ruins_vine": "mystery_fog",
    "thunder_field": "mystery_fog",
    "library_aisle": "indoor_warm",
    "tea_house": "indoor_warm",
    "candle_room": "indoor_warm",
    "greenhouse": "indoor_warm",
    "hospital_hall": "indoor_warm",
    "hot_spring": "indoor_warm",
    "airport_sunset": "rooftop_sky",
    "train_countryside": "calm_meadow",
    "desert_oasis": "sunset_hill",
    "lakeside_dock": "calm_meadow",
    "sakura_river": "campus_field",
}


def main() -> None:
    prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
    if ARCHETYPES_JSON.is_file():
        ARCHETYPE.update(json.loads(ARCHETYPES_JSON.read_text(encoding="utf-8")))
    filled = 0
    for sid in sorted(prompts):
        dst = SCENES / f"{sid}.png"
        if dst.is_file() and dst.stat().st_size > 30_000:
            continue
        arch = ARCHETYPE.get(sid, "calm_meadow")
        src = SCENES / f"{arch}.png"
        if not src.is_file():
            src = SCENES / "calm_meadow.png"
        if src.is_file():
            shutil.copy2(src, dst)
            filled += 1
            print("fallback", sid, "<-", arch)
    print("filled", filled)


if __name__ == "__main__":
    main()
