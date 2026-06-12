#!/usr/bin/env python3
"""
Post-process generated images for 2711 editor: move, resize, optional bg removal, register manifest.

Typical agent flow:
  1. GenerateImage → workspace path
  2. python scripts/process-asset.py --input <path> --category icon --id empty-story-scroll --register
  3. Wire path printed into HTML/CSS/JS
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Install Pillow: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
TEMPLATES = SCRIPTS / "art-prompt-templates.json"
MANIFEST = ROOT / "frontend" / "images" / "manifest.json"


def _load_templates() -> dict:
    return json.loads(TEMPLATES.read_text(encoding="utf-8"))


def _resolve_output(category: str, asset_id: str, fmt: str) -> Path:
    spec = _load_templates()["categories"][category]
    rel = spec["path"].format(id=asset_id)
    out = (ROOT / "frontend" / rel).resolve()
    if fmt != spec.get("format", "png"):
        out = out.with_suffix(f".{fmt}")
    return out


def _resize(img: Image.Image, size: tuple[int, int], *, cover: bool) -> Image.Image:
    if img.size == size:
        return img
    if cover:
        img = img.convert("RGBA") if img.mode not in ("RGB", "RGBA") else img
        tw, th = size
        iw, ih = img.size
        scale = max(tw / iw, th / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        return resized.crop((left, top, left + tw, top + th))
    return img.resize(size, Image.Resampling.LANCZOS)


def _edge_bg_color(img: Image.Image) -> tuple[int, int, int]:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    samples: list[tuple[int, int, int]] = []
    for x in range(w):
        samples.append(rgba.getpixel((x, 0))[:3])
        samples.append(rgba.getpixel((x, h - 1))[:3])
    for y in range(1, h - 1):
        samples.append(rgba.getpixel((0, y))[:3])
        samples.append(rgba.getpixel((w - 1, y))[:3])
    # median per channel — robust when subject touches a corner
    channels = zip(*samples)
    return tuple(sorted(ch)[len(samples) // 2] for ch in channels)  # type: ignore[return-value]


def _remove_bg_pil(img: Image.Image, *, tolerance: int = 32) -> Image.Image:
    rgba = img.convert("RGBA")
    bg = _edge_bg_color(rgba)
    w, h = rgba.size
    pixels = rgba.load()
    visited = [[False] * w for _ in range(h)]
    stack: list[tuple[int, int]] = []

    def _close(r: int, g: int, b: int) -> bool:
        return abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) <= tolerance

    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or visited[y][x]:
            continue
        r, g, b, _a = pixels[x, y]
        if not _close(r, g, b):
            continue
        visited[y][x] = True
        pixels[x, y] = (r, g, b, 0)
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    return rgba


def _remove_bg_colorkey(img: Image.Image, *, tolerance: int = 36) -> Image.Image:
    """Remove all pixels near edge-median color — good for sticker on solid backdrop."""
    rgba = img.convert("RGBA")
    bg = _edge_bg_color(rgba)
    data = rgba.getdata()
    new = []
    for r, g, b, a in data:
        dist = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
        if dist <= tolerance:
            new.append((r, g, b, 0))
        elif dist <= tolerance * 2:
            fade = min(255, int((dist - tolerance) / tolerance * 180))
            new.append((r, g, b, 255 - fade))
        else:
            new.append((r, g, b, a))
    out = Image.new("RGBA", rgba.size)
    out.putdata(new)
    return out


def _remove_bg_rembg(img: Image.Image) -> Image.Image | None:
    try:
        from rembg import remove  # type: ignore
    except ImportError:
        return None
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = remove(buf.getvalue())
    return Image.open(io.BytesIO(result)).convert("RGBA")


def remove_background(img: Image.Image, *, method: str = "auto") -> Image.Image:
    if method == "none":
        return img
    if method in ("auto", "rembg"):
        rembg_out = _remove_bg_rembg(img)
        if rembg_out is not None:
            return rembg_out
    if method in ("auto", "pil"):
        flooded = _remove_bg_pil(img)
        # If edges still opaque, subject likely fills frame — try global color key
        w, h = flooded.size
        edge_alpha = [flooded.getpixel((x, 0))[3] for x in range(w)]
        edge_alpha += [flooded.getpixel((x, h - 1))[3] for x in range(w)]
        if sum(edge_alpha) / max(len(edge_alpha), 1) > 200:
            return _remove_bg_colorkey(img)
        return flooded
    return img


def register_manifest(
    *,
    category: str,
    asset_id: str,
    rel_file: str,
    source: str,
    prompt: str = "",
) -> None:
    manifest: dict = {"ui": [], "scenes": []}
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    entry = {
        "id": asset_id,
        "file": rel_file.replace("\\", "/"),
        "source": source,
    }
    if prompt:
        entry["prompt"] = prompt

    bucket = "scenes" if category == "scene" else "ui"
    items: list = manifest.setdefault(bucket, [])
    items = [e for e in items if e.get("id") != asset_id]
    items.append(entry)
    manifest[bucket] = sorted(items, key=lambda e: e.get("id", ""))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def process_asset(
    input_path: Path,
    *,
    category: str,
    asset_id: str,
    output: Path | None = None,
    size: tuple[int, int] | None = None,
    remove_bg: bool | None = None,
    bg_method: str = "auto",
    register: bool = False,
    prompt: str = "",
    dry_run: bool = False,
) -> Path:
    templates = _load_templates()
    spec = templates["categories"][category]
    target_size = tuple(size) if size else tuple(spec["size"])
    should_remove = spec.get("remove_bg", False) if remove_bg is None else remove_bg
    out = output or _resolve_output(category, asset_id, spec.get("format", "png"))

    if dry_run:
        print(f"[dry-run] {input_path} -> {out} size={target_size} remove_bg={should_remove}")
        return out

    img = Image.open(input_path)
    if should_remove:
        img = remove_background(img, method=bg_method)
    img = _resize(img, target_size, cover=category in ("scene", "landing", "workbench"))

    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = spec.get("format", "png").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    save_kw: dict = {}
    if fmt in ("PNG", "WEBP"):
        save_kw["optimize"] = True
    if fmt == "JPEG" and img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    img.save(out, format=fmt, **save_kw)

    rel = out.relative_to(ROOT / "frontend").as_posix()
    if register:
        register_manifest(
            category=category,
            asset_id=asset_id,
            rel_file=rel,
            source="generated",
            prompt=prompt,
        )

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Process and deploy a generated 2711 asset")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Source image (GenerateImage output)")
    parser.add_argument("--category", "-c", required=True, choices=["scene", "landing", "ui", "icon", "workbench"])
    parser.add_argument("--id", required=True, help="Asset id (kebab-case or snake_case)")
    parser.add_argument("--output", "-o", type=Path, help="Override output path")
    parser.add_argument("--size", help="WxH override, e.g. 512x512")
    parser.add_argument("--remove-bg", action="store_true", help="Force background removal")
    parser.add_argument("--no-remove-bg", action="store_true", help="Skip background removal")
    parser.add_argument("--bg-method", choices=["auto", "rembg", "pil", "none"], default="auto")
    parser.add_argument("--register", "-r", action="store_true", help="Update frontend/images/manifest.json")
    parser.add_argument("--prompt", default="", help="Original prompt for manifest")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inp = args.input.expanduser().resolve()
    if not inp.is_file():
        raise SystemExit(f"Input not found: {inp}")

    size = None
    if args.size:
        w, h = args.size.lower().split("x")
        size = (int(w), int(h))

    remove_bg = None
    if args.remove_bg:
        remove_bg = True
    if args.no_remove_bg:
        remove_bg = False

    out = process_asset(
        inp,
        category=args.category,
        asset_id=args.id,
        output=args.output,
        size=size,
        remove_bg=remove_bg,
        bg_method=args.bg_method,
        register=args.register,
        prompt=args.prompt,
        dry_run=args.dry_run,
    )

    rel_frontend = out.relative_to(ROOT / "frontend").as_posix()
    print(f"OK: frontend/{rel_frontend}")
    if args.category == "scene":
        print("Next: python scripts/sync-scene-images-js.py")
    print(f"Wire: {rel_frontend}")


if __name__ == "__main__":
    main()
