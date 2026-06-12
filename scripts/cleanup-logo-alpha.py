#!/usr/bin/env python3
"""Re-process workbench logo: edge-connected flood + text-side chroma matte + despill."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = (
    ROOT
    / "frontend/images/workbench/2711-logo.png"
)
DEFAULT_OUTPUT = ROOT / "frontend/images/workbench/2711-logo-transparent.png"
DARK_BG = (0x1A, 0x1A, 0x2E)


def _edge_bg_color(img: Image.Image) -> np.ndarray:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    samples: list[tuple[int, int, int]] = []
    for x in range(w):
        samples.append(rgba.getpixel((x, 0))[:3])
        samples.append(rgba.getpixel((x, h - 1))[:3])
    for y in range(1, h - 1):
        samples.append(rgba.getpixel((0, y))[:3])
        samples.append(rgba.getpixel((w - 1, y))[:3])
    channels = zip(*samples)
    return np.array(
        [sorted(ch)[len(samples) // 2] for ch in channels],
        dtype=np.float32,
    )


def _flood_mask(rgb: np.ndarray, bg: np.ndarray, tolerance: int) -> np.ndarray:
    h, w, _ = rgb.shape
    close = np.abs(rgb - bg[None, None, :]).sum(axis=2) <= tolerance
    visited = np.zeros((h, w), dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(w):
        stack.extend([(x, 0), (x, h - 1)])
    for y in range(h):
        stack.extend([(0, y), (w - 1, y)])
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or visited[y, x] or not close[y, x]:
            continue
        visited[y, x] = True
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return visited


def _despill(
    arr: np.ndarray,
    *,
    threshold: int = 200,
    sat_max: int = 42,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    out = arr.astype(np.float32).copy()
    r, g, b, a = out[..., 0], out[..., 1], out[..., 2], out[..., 3]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    sel = (a > 4) & (a < 252) & (mx >= threshold) & (sat <= sat_max)
    if mask is not None:
        sel &= mask
    if sel.any():
        spill = np.clip((mx - threshold) / max(255 - threshold, 1), 0.0, 1.0)
        a[sel] *= 1.0 - spill[sel] * 0.92
        dark = mn[sel]
        blend = np.clip(spill[sel] * 0.9, 0.0, 1.0)
        r[sel] = r[sel] * (1.0 - blend) + dark * blend
        g[sel] = g[sel] * (1.0 - blend) + dark * blend
        b[sel] = b[sel] * (1.0 - blend) + dark * blend
    out[..., 3] = np.clip(a, 0, 255)
    out[..., :3] = np.clip(out[..., :3], 0, 255)
    return out.astype(np.uint8)


def _stats(arr: np.ndarray) -> dict:
    dark = np.array(DARK_BG, dtype=np.float32)
    h, w = arr.shape[:2]
    a = arr[..., 3]
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    edge = (a > 8) & (a < 245)
    pale_edge = edge & (mx >= 200) & (sat <= 50)
    comp = arr[..., :3].astype(np.float32) * arr[..., 3:4] / 255.0 + dark * (
        1.0 - arr[..., 3:4] / 255.0
    )
    roi = comp[int(h * 0.18) : int(h * 0.72), int(w * 0.38) : int(w * 0.98)]
    halo = ((roi[..., 0] > 195) & (roi[..., 1] > 195) & (roi[..., 2] > 195)).sum()
    return {
        "size": (w, h),
        "corner_alpha": [int(arr[0, 0, 3]), int(arr[0, -1, 3]), int(arr[-1, 0, 3]), int(arr[-1, -1, 3])],
        "partial_alpha": int(((a > 0) & (a < 255)).sum()),
        "pale_edge_pixels": int(pale_edge.sum()),
        "bright_halo_on_dark": int(halo),
    }


def process_logo(
    source: Path,
    output: Path,
    *,
    flood_tolerance: int = 32,
    matte_width: float = 18.0,
    text_split: float = 0.36,
    feather: float = 0.55,
) -> dict:
    src = np.array(Image.open(source).convert("RGB"))
    h, w, _ = src.shape
    bg = _edge_bg_color(Image.open(source))
    sat = src.max(axis=2) - src.min(axis=2)

    bg_mask = _flood_mask(src, bg, flood_tolerance)
    dist = np.abs(src.astype(np.float32) - bg[None, None, :]).sum(axis=2)
    sat_factor = np.clip(1.0 - sat / 68.0, 0.1, 1.0)
    alpha = np.clip((34.0 - dist * sat_factor) / matte_width, 0.0, 1.0)
    alpha[bg_mask] = 0.0
    alpha[(alpha > 0.65) & (sat > 14)] = 1.0
    alpha_u8 = (alpha * 255.0).astype(np.uint8)

    split = int(w * text_split)
    flood_alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    alpha_u8[:, :split] = flood_alpha[:, :split]

    arr = np.dstack([src, alpha_u8])
    text_mask = np.zeros((h, w), dtype=bool)
    text_mask[:, split:] = True
    arr = _despill(arr, threshold=198, sat_max=45, mask=text_mask)
    arr = _despill(arr, threshold=212, sat_max=35, mask=~text_mask)

    alpha_img = Image.fromarray(arr[..., 3], mode="L")
    soft = np.array(alpha_img.filter(ImageFilter.GaussianBlur(feather)), dtype=np.uint8)
    dil = np.array(alpha_img.filter(ImageFilter.MaxFilter(3)), dtype=bool)
    ero = np.array(alpha_img.filter(ImageFilter.MinFilter(3)), dtype=bool)
    band = dil ^ ero
    arr[..., 3] = np.where(band, soft, arr[..., 3])
    arr[arr[..., 3] < 5, :3] = 0

    before = _stats(arr)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, mode="RGBA").save(output, format="PNG", optimize=True)
    after = _stats(np.array(Image.open(output).convert("RGBA")))

    return {
        "source": str(source),
        "output": str(output),
        "method": "edge-flood + text chroma matte + despill",
        "params": {
            "flood_tolerance": flood_tolerance,
            "matte_width": matte_width,
            "text_split": text_split,
            "feather": feather,
        },
        "stats": after,
        "before_save": before,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean workbench logo alpha edges")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--flood-tolerance", type=int, default=32)
    parser.add_argument("--matte-width", type=float, default=18.0)
    parser.add_argument("--text-split", type=float, default=0.36)
    parser.add_argument("--feather", type=float, default=0.55)
    args = parser.parse_args()

    inp = args.input.expanduser().resolve()
    if not inp.is_file():
        raise SystemExit(f"Input not found: {inp}")

    info = process_logo(
        inp,
        args.output.expanduser().resolve(),
        flood_tolerance=args.flood_tolerance,
        matte_width=args.matte_width,
        text_split=args.text_split,
        feather=args.feather,
    )
    print("OK:", info["output"])
    print("method:", info["method"])
    print("stats:", info["stats"])


if __name__ == "__main__":
    main()
