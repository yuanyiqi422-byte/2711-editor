#!/usr/bin/env python3
"""Audit BGM mp3/ogg files with ffprobe."""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BGM_DIR = os.path.join(ROOT, "frontend", "audio", "bgm")


def audit_file(path: str) -> dict:
    fn = os.path.basename(path)
    size = os.path.getsize(path)
    entry: dict = {"filename": fn, "bytes": size, "ok": True, "issues": []}
    if size == 0:
        entry["ok"] = False
        entry["issues"].append("zero-byte")
        return entry
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,format_name,bit_rate",
                "-of",
                "json",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            entry["ok"] = False
            entry["issues"].append("ffprobe: " + (r.stderr.strip() or f"exit {r.returncode}"))
            return entry
        data = json.loads(r.stdout or "{}")
        fmt = data.get("format", {})
        dur = float(fmt.get("duration", 0) or 0)
        entry["duration"] = round(dur, 2)
        entry["format"] = fmt.get("format_name", "")
        entry["bit_rate"] = fmt.get("bit_rate")
        if dur < 1:
            entry["ok"] = False
            entry["issues"].append("duration<1s")
    except FileNotFoundError:
        entry["ok"] = False
        entry["issues"].append("ffprobe not installed")
    except Exception as e:
        entry["ok"] = False
        entry["issues"].append(str(e))
    return entry


def main() -> int:
    files = sorted(
        f
        for f in os.listdir(BGM_DIR)
        if f.lower().endswith((".mp3", ".ogg"))
    )
    results = [audit_file(os.path.join(BGM_DIR, f)) for f in files]
    bad = [r for r in results if not r["ok"]]
    print(f"TOTAL: {len(results)}")
    print(f"BAD: {len(bad)}")
    for r in results:
        status = "OK" if r["ok"] else "BAD"
        dur = r.get("duration", "?")
        print(f"{status} | {r['bytes']:>10} | {str(dur):>8}s | {r['filename']}")
        if r["issues"]:
            print(f"       issues: {r['issues']}")
    print(json.dumps({"bad": bad}, ensure_ascii=False, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
