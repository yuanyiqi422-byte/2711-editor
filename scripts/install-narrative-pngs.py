#!/usr/bin/env python3
"""Copy generated narrative PNGs from Cursor assets into frontend/scenes."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(r"C:\Users\袁艺琪\.cursor\projects\c-Users-code1\assets")
SCENES = ROOT / "frontend" / "images" / "scenes"
ARCH = json.loads((ROOT / "scripts" / "scene-archetypes.json").read_text(encoding="utf-8"))


def main() -> None:
    copied = 0
    missing = []
    for sid in sorted(ARCH):
        for name in (f"scene-{sid}.png", f"{sid}.png"):
            src = ASSETS / name
            if src.is_file():
                shutil.copy2(src, SCENES / f"{sid}.png")
                copied += 1
                print("copied", sid)
                break
        else:
            missing.append(sid)
    print(f"copied {copied}, missing {len(missing)}")
    if missing:
        print("missing:", ", ".join(missing[:20]), "..." if len(missing) > 20 else "")


if __name__ == "__main__":
    main()
