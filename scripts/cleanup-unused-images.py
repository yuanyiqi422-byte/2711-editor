#!/usr/bin/env python3
"""Remove image files not referenced by the frontend or scene library."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "frontend" / "images"
SCENES = IMG / "scenes"
PROMPTS = Path(__file__).resolve().parent / "scene-prompts.json"

# Always keep (paths relative to frontend/)
STATIC_KEEP = {
    "favicon.svg",
    "images/magic-scroll-hero.png",
    "images/floating-island-castle.png",
    "images/workshop-atmosphere.png",
    "images/overlay-petals.svg",
    "images/overlay-wind.svg",
    "images/manifest.json",
}


def rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT / "frontend").as_posix()
    except ValueError:
        return str(p)


def main() -> None:
    prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
    keep: set[str] = set(STATIC_KEEP)
    for sid in prompts:
        keep.add(f"images/scenes/{sid}.png")

    removed = 0
    freed = 0
    for path in sorted(IMG.rglob("*")):
        if not path.is_file():
            continue
        key = rel(path)
        if key in keep:
            continue
        size = path.stat().st_size
        path.unlink()
        removed += 1
        freed += size
        print("removed", key)

    print(f"Done: removed {removed} files, freed {freed / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
