#!/usr/bin/env python3
"""Build horizontal workbench logo: flood-fill icon + gradient wordmark."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = Path(
    r"C:\Users\袁艺琪\.cursor\projects\c-Users-code1\assets"
    r"\c__Users_____AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    r"IMG_3012-26f50f06-d685-4cde-afaa-23f922324c7d.png"
)
DEFAULT_OUTPUT = ROOT / "frontend/images/workbench/2711-logo-transparent.png"
TEXT = "2711编辑器"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\NotoSerifSC-Bold.otf",
    r"C:\Windows\Fonts\NotoSerifSC-Regular.otf",
    r"C:\Windows\Fonts\simhei.ttf",
]


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


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _icon_rgba(source: Path, *, flood_tolerance: int = 40) -> Image.Image:
    src = Image.open(source).convert("RGBA")
    rgb = np.array(src.convert("RGB"))
    bg = _edge_bg_color(src)
    bg_mask = _flood_mask(rgb, bg, flood_tolerance)
    arr = np.array(src)
    arr[bg_mask, 3] = 0
    arr[arr[..., 3] < 8, :3] = 0
    icon = Image.fromarray(arr, mode="RGBA")
    bbox = icon.getbbox()
    if bbox:
        icon = icon.crop(bbox)
    return icon


def _gradient_text_layer(
    text: str,
    *,
    font_size: int,
    width: int,
    height: int,
) -> Image.Image:
    font = _load_font(font_size)
    tmp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = max(0, (width - tw) // 2 - bbox[0])
    y = max(0, (height - th) // 2 - bbox[1])

    grad = Image.new("RGBA", (tw, th))
    gdraw = ImageDraw.Draw(grad)
    for px in range(tw):
        t = px / max(tw - 1, 1)
        r = int(232 * (1 - t) + 244 * t)
        g = int(200 * (1 - t) + 239 * t)
        b = int(120 * (1 - t) + 230 * t)
        gdraw.line([(px, 0), (px, th)], fill=(r, g, b, 255))

    mask = Image.new("L", (width, height), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.text((x, y), text, font=font, fill=255)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    layer.paste(grad, (x + bbox[0], y + bbox[1]), mask.crop((x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3])))
    return Image.composite(layer, Image.new("RGBA", (width, height), (0, 0, 0, 0)), mask)


def build_lockup(
    source: Path,
    output: Path,
    *,
    flood_tolerance: int = 40,
    gap: int = 24,
    text_pad: int = 12,
) -> tuple[int, int]:
    icon = _icon_rgba(source, flood_tolerance=flood_tolerance)
    icon_h = icon.height
    font_size = max(36, int(icon_h * 0.34))

    font = _load_font(font_size)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = probe.textbbox((0, 0), TEXT, font=font)
    text_w = bbox[2] - bbox[0] + text_pad * 2
    text_h = icon_h

    canvas_w = icon.width + gap + text_w
    canvas_h = icon_h
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    canvas.paste(icon, (0, (canvas_h - icon.height) // 2), icon)

    text_layer = _gradient_text_layer(
        TEXT,
        font_size=font_size,
        width=text_w,
        height=text_h,
    )
    canvas.paste(text_layer, (icon.width + gap, 0), text_layer)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    return canvas.size


def main() -> None:
    parser = argparse.ArgumentParser(description="Build workbench logo lockup PNG")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--flood-tolerance", type=int, default=40)
    args = parser.parse_args()

    inp = args.input.expanduser().resolve()
    if not inp.is_file():
        raise SystemExit(f"Input not found: {inp}")

    size = build_lockup(inp, args.output.expanduser().resolve(), flood_tolerance=args.flood_tolerance)
    print(f"OK: {args.output} ({size[0]}x{size[1]})")


if __name__ == "__main__":
    main()
