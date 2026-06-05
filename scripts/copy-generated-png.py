#!/usr/bin/env python3
"""Copy a generated PNG from Cursor assets into frontend/images/scenes/{id}.png"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENES = ROOT / "frontend" / "images" / "scenes"
ASSETS = Path(r"C:\Users\袁艺琪\.cursor\projects\c-Users-code1\assets")


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: copy-generated-png.py <scene_id> <source_png>")
        sys.exit(1)
    scene_id, src = sys.argv[1], Path(sys.argv[2])
    if not src.is_file():
        alt = ASSETS / f"{scene_id}.png"
        if alt.is_file():
            src = alt
        else:
            print("missing source", src)
            sys.exit(1)
    SCENES.mkdir(parents=True, exist_ok=True)
    dst = SCENES / f"{scene_id}.png"
    shutil.copy2(src, dst)
    print("copied", dst, dst.stat().st_size)


if __name__ == "__main__":
    main()
