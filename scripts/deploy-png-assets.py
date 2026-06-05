#!/usr/bin/env python3
"""Deploy Ghibli PNG assets: landing + 62 scene backgrounds."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    raise SystemExit("Install Pillow: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(r"C:\Users\袁艺琪\.cursor\projects\c-Users-code1\assets")
IMG = ROOT / "frontend" / "images"
SCENES = IMG / "scenes"
TARGET_SIZE = (1920, 1080)

LANDING = [
    "hero-ghibli.png",
    "feature-branches.png",
    "feature-transform.png",
    "feature-play.png",
    "workshop-atmosphere.png",
]

# Direct AI master -> scene id (file scene-{id}.png in assets)
DIRECT = [
    "calm_meadow", "forest_path", "rainy_street", "city_lights", "romance_cafe",
    "xianxia_peaks", "beach_wind", "winter_snow", "mystery_fog", "school_corridor",
    "train_countryside", "shrine_path", "night_stars", "sunset_hill", "campus_field",
    "indoor_warm", "cherry_tunnel", "hot_spring", "floating_isles", "desert_oasis",
    "library_aisle", "harbor_dawn", "rooftop_sky", "lantern_festival", "storm_coast",
    "cave_glow", "rice_terraces", "night_bazaar",
]

# scene_id -> master id for PIL-derived variants
DERIVED: dict[str, str] = {
    "airport_sunset": "sunset_hill",
    "autumn_road": "sunset_hill",
    "balcony_night": "city_lights",
    "bamboo_grove": "forest_path",
    "bamboo_rain": "rainy_street",
    "campsite": "night_stars",
    "canal_twilight": "harbor_dawn",
    "candle_room": "indoor_warm",
    "castle_clouds": "floating_isles",
    "cliff_lighthouse": "beach_wind",
    "clock_tower": "city_lights",
    "crystal_spring": "hot_spring",
    "enchanted_grove": "forest_path",
    "flower_field": "calm_meadow",
    "ghost_mansion": "mystery_fog",
    "greenhouse": "indoor_warm",
    "hospital_hall": "school_corridor",
    "lakeside_dock": "harbor_dawn",
    "market_alley": "night_bazaar",
    "meadow_windmill": "calm_meadow",
    "moon_bridge": "shrine_path",
    "observatory": "night_stars",
    "pagoda_mist": "xianxia_peaks",
    "ruins_vine": "mystery_fog",
    "sakura_river": "cherry_tunnel",
    "sky_tram": "train_countryside",
    "snow_shrine": "winter_snow",
    "subway_night": "city_lights",
    "tea_house": "romance_cafe",
    "thunder_field": "storm_coast",
    "village_dusk": "sunset_hill",
    "volcano_dusk": "xianxia_peaks",
    "waterfall_rainbow": "forest_path",
    "windy_hill": "calm_meadow",
}

ALL_SCENES = sorted(set(DIRECT) | set(DERIVED.keys()))


def _seed(scene_id: str) -> int:
    return int(hashlib.md5(scene_id.encode()).hexdigest()[:8], 16)


def fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    img = img.convert("RGB")
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def variant(img: Image.Image, scene_id: str) -> Image.Image:
    s = _seed(scene_id)
    w, h = img.size
    shift = (s % 7) * 24
    cropped = img.crop((shift, 0, min(w, shift + w - 48), h))
    out = fit_cover(cropped, TARGET_SIZE)
    bright = 0.88 + (s % 13) / 100.0
    color = 0.92 + (s % 11) / 100.0
    out = ImageEnhance.Brightness(out).enhance(bright)
    out = ImageEnhance.Color(out).enhance(color)
    if s % 2:
        out = ImageOps.mirror(out)
    return out


def master_path(master_id: str) -> Path:
    p = ASSETS / f"scene-{master_id}.png"
    if not p.is_file():
        raise FileNotFoundError(f"Missing master: {p}")
    return p


def main() -> None:
    SCENES.mkdir(parents=True, exist_ok=True)

    for name in LANDING:
        src = ASSETS / name
        if not src.is_file():
            raise FileNotFoundError(f"Missing landing asset: {src}")
        dst = IMG / name
        img = fit_cover(Image.open(src), TARGET_SIZE if "hero" in name or "workshop" in name else (1600, 1000))
        img.save(dst, "PNG", optimize=True)
        print("landing", dst.name)

    for sid in DIRECT:
        src = master_path(sid)
        dst = SCENES / f"{sid}.png"
        fit_cover(Image.open(src), TARGET_SIZE).save(dst, "PNG", optimize=True)
        print("scene direct", sid)

    for sid, master in DERIVED.items():
        base = fit_cover(Image.open(master_path(master)), TARGET_SIZE)
        variant(base, sid).save(SCENES / f"{sid}.png", "PNG", optimize=True)
        print("scene derived", sid, "<-", master)

    assert len(list(SCENES.glob("*.png"))) >= 62, "Expected 62+ scene PNGs"
    print(f"Done: {len(list(SCENES.glob('*.png')))} scene PNGs, {len(LANDING)} landing PNGs")


if __name__ == "__main__":
    main()
