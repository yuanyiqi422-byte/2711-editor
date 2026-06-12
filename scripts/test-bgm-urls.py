#!/usr/bin/env python3
"""Verify BGM files on disk and via HTTP (JS encodeURIComponent paths).

Runtime skip list: MusicPicker.markFailed(filename) / getFailedFilenames()
after this script flags missing or zero-byte files.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BGM_DIR = os.path.join(ROOT, "frontend", "audio", "bgm")
BASE = "http://127.0.0.1:8010/"

FILES = {
    "journey": "Journey.mp3",
    "loveDeepspace": "Love And Deepspace.mp3",
    "dollHouse": "岩崎琢 - 人形の館.mp3",
    "kikujiro": "菊次郎的夏天：Summer-Silu+Wang&久石让.mp3",
    "littleStory": "Valentin-A Little Story.mp3",
    "timeToLove": "OCTOBER - Time to love_20867599.mp3",
    "skyChildren": "Choefeker _ Faolan - Sky_Children of the light (feat_ Faolan).ogg",
    "ayasaConfession": "Ayasa绚沙 - 告白の夜 (告白之夜) (LIVE!! Ayasa Theater episode 7).ogg",
    "reverseAlisa": "Reverse - ALisa.mp3",
    "hisTheme": "Toby Fox - His Theme.mp3",
    "toTheMoon": "To the moon.mp3",
    "easternThought": "Kevin_MacLeod-Eastern_Thought.mp3",
    "ishikariLore": "Kevin_MacLeod-Ishikari_Lore.mp3",
    "ripplesGuzheng": "Kevin_MacLeod-Ripples_guzheng.mp3",
    "nightOnDocks": "Kevin_MacLeod-Night_on_the_Docks.mp3",
    "bossaAntigua": "Kevin_MacLeod-Bossa_Antigua.mp3",
    "floatingCities": "Kevin_MacLeod-Floating_Cities.mp3",
    "mysterySoft": "HoliznaCC0 - Mystery (CC0).mp3",
    "atmosphereSoft": "HoliznaCC0 - Atmosphere 1 (CC0).mp3",
    "driftingPianoSoft": "HoliznaCC0 - Drifting Piano (CC0).mp3",
    "campusSoftPiano": "campus_soft_piano.mp3",
    "schoolRomanceAcoustic": "school_romance_acoustic.mp3",
    "sliceOfLifeLofi": "slice_of_life_lofi_quiet.mp3",
    "xianxiaXiaoMist": "xianxia_xiao_mist.mp3",
    "xianxiaGuzhengMist": "xianxia_guzheng_mist.mp3",
    "xianxiaPipaAmbient": "xianxia_pipa_ambient.mp3",
    "dhakaSoftAsian": "Kevin_MacLeod-Dhaka_soft_asian.mp3",
    "pixabayDiziFlute": "Pixabay-Chinese_Dizi_Flute.mp3",
    "pixabayCloudsPagoda": "Pixabay-Clouds_Ancient_Pagoda.mp3",
    "pixabayGuzhengJourney": "Pixabay-Mystical_Guzheng_Journey.mp3",
    "holiznaDriftingPianoNight": "holizna-drifting-piano-night.mp3",
    "holiznaShimmerChill": "holizna-shimmer-chill-ambient.mp3",
    "holiznaSpringHorizon": "holizna-spring-on-horizon-soft-orchestra.mp3",
    "holiznaWaitingCalmStudy": "holizna-waiting-around-calm-study.mp3",
    "holiznaYetAgainPeaceful": "holizna-yet-again-peaceful-lofi.mp3",
}

# MP3 fallbacks for OGG-only tracks (not in FILES; resolved at runtime)
OGG_MP3_FALLBACKS = {
    FILES["skyChildren"]: "sky_children.mp3",
    FILES["ayasaConfession"]: "ayasa_confession_night.mp3",
}

EXPECTED_TRACK_COUNT = len(FILES)


def js_encode_uri_component(s: str) -> str:
    """Match JavaScript encodeURIComponent (RFC 3986 unreserved + subset)."""
    return urllib.parse.quote(s, safe="-_.!~*'()")


def main() -> int:
    results = []
    http_ok = True
    disk_ok = True

    assert EXPECTED_TRACK_COUNT == 35, f"FILES count {EXPECTED_TRACK_COUNT}, expected 35"

    for key, filename in FILES.items():
        disk_path = os.path.join(BGM_DIR, filename)
        disk_exists = os.path.isfile(disk_path)
        if not disk_exists:
            disk_ok = False

        rel = "audio/bgm/" + js_encode_uri_component(filename)
        url = BASE + rel
        http_status = None
        http_len = None
        http_err = None
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=8) as resp:
                http_status = resp.status
                http_len = resp.headers.get("Content-Length")
        except urllib.error.HTTPError as e:
            http_status = e.code
            http_err = str(e)
            http_ok = False
        except Exception as e:
            http_err = str(e)
            http_ok = False

        results.append({
            "key": key,
            "filename": filename,
            "disk_exists": disk_exists,
            "disk_bytes": os.path.getsize(disk_path) if disk_exists else 0,
            "url": rel,
            "http_status": http_status,
            "http_len": http_len,
            "http_err": http_err,
        })

    for ogg_name, mp3_name in OGG_MP3_FALLBACKS.items():
        disk_path = os.path.join(BGM_DIR, mp3_name)
        disk_exists = os.path.isfile(disk_path)
        if not disk_exists:
            disk_ok = False
        rel = "audio/bgm/" + js_encode_uri_component(mp3_name)
        url = BASE + rel
        http_status = None
        http_len = None
        http_err = None
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=8) as resp:
                http_status = resp.status
                http_len = resp.headers.get("Content-Length")
        except urllib.error.HTTPError as e:
            http_status = e.code
            http_err = str(e)
            http_ok = False
        except Exception as e:
            http_err = str(e)
            http_ok = False
        results.append({
            "key": "fallback:" + mp3_name,
            "filename": mp3_name,
            "fallback_for": ogg_name,
            "disk_exists": disk_exists,
            "disk_bytes": os.path.getsize(disk_path) if disk_exists else 0,
            "url": rel,
            "http_status": http_status,
            "http_len": http_len,
            "http_err": http_err,
        })

    print(json.dumps({
        "track_count": EXPECTED_TRACK_COUNT,
        "disk_ok": disk_ok,
        "http_ok": http_ok,
        "tracks": results,
    }, ensure_ascii=False, indent=2))
    return 0 if disk_ok and http_ok else 1


if __name__ == "__main__":
    sys.exit(main())
