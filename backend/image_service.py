"""Optional AI scene image generation with disk cache."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "scene_cache"
DEFAULT_IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1792x1024"


def _image_api_key() -> str:
    key = os.getenv("IMAGE_API_KEY", "").strip()
    if key and key != "your-secret-key-here":
        return key
    key = os.getenv("AI_API_KEY", "").strip()
    if key and key != "your-secret-key-here":
        return key
    return ""


def _image_api_base() -> str:
    base = os.getenv("IMAGE_API_BASE", "").strip()
    if base:
        return base.rstrip("/")
    return os.getenv("AI_API_BASE", "https://api.openai.com/v1").rstrip("/")


def _image_model() -> str:
    return os.getenv("IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL


def is_image_gen_configured() -> bool:
    """True when an image-capable API key and base URL are present."""
    if not _image_api_key():
        return False
    base = _image_api_base()
    if "deepseek.com" in base and not os.getenv("IMAGE_API_BASE", "").strip():
        return False
    return True


def _cache_path(cache_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-f0-9]", "", cache_id.lower())[:64]
    return CACHE_DIR / f"{safe}.png"


def cache_id_for(prompt: str, mood: str) -> str:
    raw = f"{mood.strip().lower()}|{prompt.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def read_cached_image(cache_id: str) -> bytes | None:
    path = _cache_path(cache_id)
    if path.is_file():
        return path.read_bytes()
    return None


def _build_prompt(prompt: str, mood: str) -> str:
    mood_hint = mood.replace("_", " ").strip() or "neutral"
    base = (
        "Soft watercolor landscape background, blue-pink-green palette, "
        "atmospheric, no text, no watermark, no characters. "
    )
    return f"{base}Mood: {mood_hint}. Scene: {prompt.strip()}"


async def generate_scene_image(prompt: str, mood: str = "neutral") -> bytes | None:
    """Generate or return cached PNG bytes. Returns None when not configured or on failure."""
    if not prompt.strip():
        return None
    if not is_image_gen_configured():
        return None

    cache_id = cache_id_for(prompt, mood)
    cached = read_cached_image(cache_id)
    if cached:
        return cached

    full_prompt = _build_prompt(prompt, mood)
    base = _image_api_base()
    key = _image_api_key()
    model = _image_model()
    url = f"{base}/images/generations"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "size": IMAGE_SIZE,
        "n": 1,
        "response_format": "b64_json",
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        items = data.get("data") or []
        if not items:
            return None
        b64 = items[0].get("b64_json")
        if b64:
            raw = base64.b64decode(b64)
        else:
            url_field = items[0].get("url")
            if not url_field:
                return None
            async with httpx.AsyncClient(timeout=120.0) as client:
                img_resp = await client.get(url_field)
            if img_resp.status_code >= 400:
                return None
            raw = img_resp.content

        out = _cache_path(cache_id)
        out.write_bytes(raw)
        return raw
    except Exception as exc:
        logger.warning("scene image generation failed: %s", exc)
        return None
