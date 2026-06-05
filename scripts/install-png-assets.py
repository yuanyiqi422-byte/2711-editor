#!/usr/bin/env python3
"""Copy generated PNG assets into frontend/images and scenes/."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(r"C:\Users\袁艺琪\.cursor\projects\c-Users-code1\assets")
IMAGES = ROOT / "frontend" / "images"
SCENES = IMAGES / "scenes"
PROMPTS = Path(__file__).resolve().parent / "scene-prompts.json"

LANDING = [
    "hero-ghibli",
    "feature-branches",
    "feature-transform",
    "feature-play",
    "workshop-atmosphere",
]


def rasterize_svg(svg: Path, png: Path) -> bool:
    try:
        import cairosvg  # type: ignore
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cairosvg", "-q"])
        import cairosvg  # type: ignore
    png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1920, output_height=1080)
    return png.is_file()


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    SCENES.mkdir(parents=True, exist_ok=True)

    for name in LANDING:
        src = ASSETS / f"{name}.png"
        if src.is_file():
            shutil.copy2(src, IMAGES / f"{name}.png")
            print("landing", name)

    prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
    ai_count = 0
    raster_count = 0
    for sid in sorted(prompts):
        dst = SCENES / f"{sid}.png"
        if dst.is_file() and dst.stat().st_size > 50_000:
            continue
        src = ASSETS / f"{sid}.png"
        if src.is_file():
            shutil.copy2(src, dst)
            ai_count += 1
            print("ai scene", sid)
            continue
        svg = SCENES / f"{sid}.svg"
        if svg.is_file():
            try:
                if rasterize_svg(svg, dst):
                    raster_count += 1
                    print("raster", sid)
            except OSError as exc:
                print("skip raster", sid, exc)

    print(f"done: ai={ai_count} raster_fallback={raster_count}")


if __name__ == "__main__":
    main()
