"""Download Batch 1/5 campus + romance gentle BGM (CC0 FMA HoliznaCC0)."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Local filename -> (FMA page URL, original title)
TRACKS = {
    "campus_soft_piano.mp3": (
        "https://freemusicarchive.org/music/holiznacc0/background-music/game-travel-1-piano/",
        "Game Travel 1 (Piano)",
    ),
    "school_romance_acoustic.mp3": (
        "https://freemusicarchive.org/music/holiznacc0/background-music/vst-guitar/",
        "VST guitar",
    ),
    "slice_of_life_lofi_quiet.mp3": (
        "https://freemusicarchive.org/music/holiznacc0/public-domain-lofi/one-night-in-france-lofi-nostalgic-chill/",
        "One Night In France (LoFi, Nostalgic, Chill)",
    ),
}

LICENSE = "CC0 1.0 Universal — HoliznaCC0 / Free Music Archive"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


def fetch_file_url(page_url: str) -> str | None:
    req = urllib.request.Request(page_url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    match = re.search(r'"fileUrl":"([^"]+)"', html)
    if match:
        return match.group(1).replace("\\/", "/")
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
                return resp.read()
        except Exception as exc:
            last_err = exc
            print(f"  retry {attempt + 1}/{retries}: {exc}")
    raise last_err or RuntimeError("download failed")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "frontend" / "audio" / "bgm"
    cmd = sys.argv[1] if len(sys.argv) > 1 else "download"

    if cmd == "urls":
        for filename, (page, title) in TRACKS.items():
            try:
                url = fetch_file_url(page)
                print(f"{filename}\t{url or 'NOT_FOUND'}\t{page}\t{title}")
            except Exception as exc:
                print(f"{filename}\tERROR:{exc}\t{page}")
        return 0

    results = []
    for filename, (page, title) in TRACKS.items():
        dest = out_dir / filename
        if dest.exists() and dest.stat().st_size > 100_000:
            print(f"Skip existing {filename}")
            results.append({"filename": filename, "ok": True, "skipped": True, "source_url": page})
            continue
        print(f"Fetching {title} ...")
        mp3_url = fetch_file_url(page)
        if not mp3_url:
            print(f"  NOT FOUND: {page}")
            results.append({"filename": filename, "ok": False, "source_url": page})
            continue
        data = download_bytes(mp3_url)
        dest.write_bytes(data)
        print(f"  -> {dest.name} ({len(data) / (1024 * 1024):.2f} MB)")
        results.append(
            {
                "filename": filename,
                "ok": True,
                "title": title,
                "license": LICENSE,
                "license_url": LICENSE_URL,
                "source_url": page,
                "download_url": mp3_url,
                "bytes": len(data),
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
