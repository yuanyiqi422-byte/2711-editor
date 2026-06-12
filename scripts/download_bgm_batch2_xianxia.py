"""Download Batch 2/5 ancient/xianxia gentle BGM (guzheng, xiao, soft pipa)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BGM_DIR = ROOT / "frontend" / "audio" / "bgm"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
HEADERS = {"User-Agent": UA}

# Skip if these already cover the same instrument (batch Task D overlap)
SKIP_IF_EXISTS = {
    "xianxia_guzheng_mist.mp3": [
        "Kevin_MacLeod-Ripples_guzheng.mp3",
        "Pixabay-Mystical_Guzheng_Journey.mp3",
    ],
    "xianxia_xiao_mist.mp3": ["Pixabay-Chinese_Dizi_Flute.mp3"],
}

TRACKS = [
    {
        "filename": "xianxia_xiao_mist.mp3",
        "title": "Nu Flute",
        "artist": "Kevin MacLeod",
        "instruments": "dizi / xiao bamboo flute",
        "license": "CC BY 3.0",
        "source_page": "https://freemusicbg.com/nu-flute/",
        "kind": "freemusicbg",
        "slug": "nu-flute",
    },
    {
        "filename": "xianxia_guzheng_mist.mp3",
        "title": "Guzheng City",
        "artist": "Kevin MacLeod",
        "instruments": "guzheng zither, gentle ambient",
        "license": "CC BY 4.0",
        "source_page": "https://incompetech.com/music/royalty-free/index.html?isrc=USUAN2100001",
        "kind": "direct",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Guzheng%20City.mp3",
    },
    {
        "filename": "xianxia_pipa_ambient.mp3",
        "title": "Moonlit Whispers",
        "artist": "kaazoom",
        "instruments": "soft pipa, guzheng, traditional Chinese ambient",
        "license": "Pixabay Content License",
        "source_page": "https://pixabay.com/music/china-moonlit-whispers-chinese-music-traditional-instruments-353045/",
        "kind": "pixabay",
        "page": "https://pixabay.com/music/china-moonlit-whispers-chinese-music-traditional-instruments-353045/",
    },
]


def curl_download(url: str, dest: Path, resume: bool = False) -> int:
    cmd = ["curl.exe", "-L", "-A", UA, "-o", str(dest), "-w", "%{http_code}", "--max-time", "300"]
    if resume:
        cmd.insert(1, "-C")
        cmd.insert(2, "-")
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    code = proc.stdout.strip()[-3:] if proc.stdout else "000"
    return int(code) if code.isdigit() else 0


def freemusicbg_id(slug: str) -> int | None:
    req = urllib.request.Request(f"https://freemusicbg.com/{slug}/", headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    m = re.search(r'data-track="(\d+)"', html) or re.search(r"playmp3\.php\?id=(\d+)", html)
    return int(m.group(1)) if m else None


def pixabay_mp3_url(page: str) -> str | None:
    proc = subprocess.run(
        ["curl.exe", "-L", "-A", UA, "-s", "--max-time", "60", page],
        capture_output=True,
    )
    html = proc.stdout.decode("utf-8", "replace") if proc.stdout else ""
    for pat in (
        r"https://cdn\.pixabay\.com/download/audio/[^\"\\]+?\.mp3[^\"\\]*",
        r"https://cdn\.pixabay\.com/audio/[^\"\\]+?\.mp3[^\"\\]*",
    ):
        m = re.search(pat, html)
        if m:
            return m.group(0).replace("\\/", "/")
    return None


def is_valid_mp3(path: Path, min_bytes: int = 200_000) -> bool:
    if not path.exists() or path.stat().st_size < min_bytes:
        return False
    head = path.read_bytes()[:3]
    return head.startswith(b"ID3") or head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3"


def should_skip_new(track: dict) -> str | None:
    dest = BGM_DIR / track["filename"]
    if is_valid_mp3(dest):
        return "already valid"
    alts = SKIP_IF_EXISTS.get(track["filename"], [])
    for alt in alts:
        p = BGM_DIR / alt
        if is_valid_mp3(p) and track["filename"] == "xianxia_guzheng_mist.mp3":
            # still download Guzheng City — different guzheng piece from Ripples/Mystical
            continue
        if is_valid_mp3(p) and track["filename"] == "xianxia_xiao_mist.mp3":
            # Nu Flute is distinct from short Pixabay dizi clip; keep both names
            continue
    return None


def download_track(track: dict) -> dict:
    dest = BGM_DIR / track["filename"]
    skip = should_skip_new(track)
    if skip:
        print(f"Skip {track['filename']}: {skip}")
        return {**track, "ok": True, "skipped": True, "path": str(dest)}

    print(f"Downloading {track['filename']} ({track['title']}) ...")
    url: str | None = None
    if track["kind"] == "direct":
        url = track["url"]
    elif track["kind"] == "freemusicbg":
        tid = freemusicbg_id(track["slug"])
        if not tid:
            return {**track, "ok": False, "error": "freemusicbg id not found"}
        url = f"https://freemusicbg.com/api/playmp3.php?id={tid}&action=download"
    elif track["kind"] == "pixabay":
        url = pixabay_mp3_url(track["page"])
        if not url:
            return {**track, "ok": False, "error": "pixabay cdn url not found"}

    tmp = dest.with_suffix(".part")
    code = curl_download(url, tmp)
    if not is_valid_mp3(tmp):
        tmp.unlink(missing_ok=True)
        return {**track, "ok": False, "error": f"bad mp3 (http {code})", "url": url}
    tmp.replace(dest)
    size = dest.stat().st_size
    print(f"  -> {dest.name} ({size / (1024 * 1024):.2f} MB)")
    return {**track, "ok": True, "bytes": size, "download_url": url}


def main() -> int:
    BGM_DIR.mkdir(parents=True, exist_ok=True)
    results = [download_track(t) for t in TRACKS]
    print(json.dumps(results, indent=2, ensure_ascii=False))
    ok = sum(1 for r in results if r.get("ok"))
    return 0 if ok >= 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
