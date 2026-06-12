#!/usr/bin/env python3
"""Crop book+quill icon (left region) from workbench logo PNG."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "frontend/images/workbench/2711-logo-transparent.png"
DEFAULT_OUTPUT = ROOT / "frontend/images/workbench/2711-icon-transparent.png"


def detect_icon_bbox(
    alpha: np.ndarray,
    *,
    text_split_ratio: float = 0.42,
    alpha_thresh: int = 20,
    padding: int = 8,
) -> tuple[int, int, int, int]:
    """Return PIL crop box (left, upper, right, lower) for icon-only region."""
    h, w = alpha.shape
    split = int(w * text_split_ratio)
    left_region = alpha[:, :split]
    ys, xs = np.where(left_region > alpha_thresh)
    if ys.size == 0:
        raise ValueError("No icon pixels found in left region of source")

    left_x = max(0, int(xs.min()) - padding)
    top_y = max(0, int(ys.min()) - padding)
    right_x = min(w, int(xs.max()) + padding + 1)
    bottom_y = min(h, int(ys.max()) + padding + 1)
    return left_x, top_y, right_x, bottom_y


def crop_workbench_icon(
    source: Path,
    output: Path,
    *,
    text_split_ratio: float = 0.42,
    alpha_thresh: int = 20,
    padding: int = 8,
) -> dict:
    im = Image.open(source).convert("RGBA")
    arr = np.array(im)
    box = detect_icon_bbox(
        arr[..., 3],
        text_split_ratio=text_split_ratio,
        alpha_thresh=alpha_thresh,
        padding=padding,
    )
    cropped = im.crop(box)
    output.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output, format="PNG", optimize=True)
    return {
        "source": str(source),
        "output": str(output),
        "crop_box": {
            "left": box[0],
            "top": box[1],
            "right": box[2],
            "bottom": box[3],
        },
        "source_size": list(im.size),
        "output_size": list(cropped.size),
        "params": {
            "text_split_ratio": text_split_ratio,
            "alpha_thresh": alpha_thresh,
            "padding": padding,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop workbench icon from logo")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--text-split", type=float, default=0.42)
    parser.add_argument("--alpha-thresh", type=int, default=20)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    inp = args.input.expanduser().resolve()
    if not inp.is_file():
        raise SystemExit(f"Input not found: {inp}")

    info = crop_workbench_icon(
        inp,
        args.output.expanduser().resolve(),
        text_split_ratio=args.text_split,
        alpha_thresh=args.alpha_thresh,
        padding=args.padding,
    )
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print("OK:", info["output"])
        print("crop_box:", info["crop_box"])
        print("output_size:", info["output_size"])


if __name__ == "__main__":
    main()
