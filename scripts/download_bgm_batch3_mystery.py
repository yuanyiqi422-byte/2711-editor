"""Download CC0 mystery/suspense ambient tracks (batch 3/5) from Free Music Archive."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# HoliznaCC0 — CC0 1.0 Universal (public domain)
TRACKS = {
    "HoliznaCC0 - Mystery (CC0).mp3": (
        "https://freemusicarchive.org/music/holiznacc0/retro-gamer-soundtrack/mystery-1/",
        "Mystery",
        "CC0 1.0 — HoliznaCC0 / Free Music Archive",
    ),
    "HoliznaCC0 - Atmosphere 1 (CC0).mp3": (
        "https://freemusicarchive.org/music/holiznacc0/retro-gamer-soundtrack/atmosphere-1-1/",
        "Atmosphere 1",
        "CC0 1.0 — HoliznaCC0 / Free Music Archive",
    ),
    "HoliznaCC0 - Drifting Piano (CC0).mp3": (
        "https://freemusicarchive.org/music/holiznacc0/background-music/drifting-piano/",
        "Drifting Piano",
        "CC0 1.0 — HoliznaCC0 / Free Music Archive",
    ),
}


def fetch_file_url(page_url: str) -> str | None:
    req = urllib.request.Request(page_url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    match = re.search(r'"fileUrl":"([^"]+)"', html)
    if match:
        return match.group(1).replace("\\/", "/")
    # fallback patterns
    for pat in (
        r"https://files\.freemusicarchive\.org[^\"\\]+?\.mp3",
        r"files\.freemusicarchive\.org[^\"\\]+?\.mp3",
    ):
        m = re.search(pat, html)
        if m:
            url = m.group(0).replace("\\/", "/")
            return url if url.startswith("http") else "https://" + url
    return None


def download_bytes(url: str, retries: int = 3) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as resp:
                chunks: list[bytes] = []
                while True:
                    block = resp.read(256 * 1024)
                    if not block:
                        break
                    chunks.append(block)
                return b"".join(chunks)
        except Exception as exc:
            last_err = exc
            print(f"  retry {attempt + 1}/{retries}: {exc}")
    raise last_err or RuntimeError("download failed")


def download(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for filename, (page, title, license_note) in TRACKS.items():
        print(f"Fetching {title} ...")
        mp3_url = fetch_file_url(page)
        if not mp3_url:
            print(f"  NOT FOUND: {page}")
            results.append({"filename": filename, "ok": False, "page": page})
            continue
        dest = out_dir / filename
        req = urllib.request.Request(mp3_url, headers=HEADERS)
        data = download_bytes(mp3_url)
        dest.write_bytes(data)
        size_mb = len(data) / (1024 * 1024)
        print(f"  -> {dest.name} ({size_mb:.2f} MB)")
        results.append(
            {
                "filename": filename,
                "ok": True,
                "title": title,
                "license": license_note,
                "source_url": page,
                "download_url": mp3_url,
                "bytes": len(data),
            }
        )
    return results


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("frontend/audio/bgm")
    info = download(target)
    print(json.dumps(info, indent=2, ensure_ascii=False))
