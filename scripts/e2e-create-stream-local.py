"""Local E2E: POST /api/create/stream with ~20k chars; log progress timeline."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8010"
URL = f"{BASE}/api/create/stream"
TARGET_CHARS = 20_000

PARAGRAPH = (
    "在一个遥远的仙侠世界里，少年林风自幼失去双亲，被青云门长老收养。"
    "他天赋平平，却有一颗不屈的心。某日，他在后山修炼时，意外发现一枚古老的玉佩。"
    "玉佩中传来神秘声音，指引他前往禁地寻找失落的剑诀。林风不顾同门劝阻，独自闯入禁地。"
    "在那里，他遇到了被封印千年的剑灵，也揭开了自己身世的秘密。"
    "原来，他的血脉中流淌着上古剑仙的力量。从此，他踏上了一条充满抉择的修行之路。"
    "每一个选择，都将改变他的命运，也将影响整个修仙界的格局。"
)


def build_text(target: int) -> str:
    parts: list[str] = []
    total = 0
    i = 0
    while total < target:
        chunk = f"【第{i + 1}幕】{PARAGRAPH}"
        parts.append(chunk)
        total += len(chunk)
        i += 1
    text = "".join(parts)
    if len(text) > target + 500:
        text = text[:target]
    return text


def parse_sse_chunk(raw: str, timeline: list[tuple[float, int, str]]) -> None:
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        evt = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                evt = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].strip()
        if not data:
            continue
        t = time.perf_counter()
        if evt == "status":
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                timeline.append((t, -1, data[:120]))
                continue
            pct = int(payload.get("progress") or 0)
            msg = str(payload.get("msg") or "")
            timeline.append((t, pct, msg))
            print(f"[{pct:3d}%] {msg}")
        elif evt in ("error", "done"):
            timeline.append((t, 100 if evt == "done" else -2, data[:200]))
            print(f"[{evt}] {data[:400]}")


def main() -> int:
    text = build_text(TARGET_CHARS)
    print(f"POST {URL}")
    print(f"text_chars={len(text)} style=xianxia")
    payload = json.dumps({"text": text, "style": "xianxia"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    timeline: list[tuple[float, int, str]] = []
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp:
            print(f"HTTP {resp.status} Content-Type: {resp.headers.get('Content-Type', '')}")
            buf = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buf:
                    part, buf = buf.split("\n\n", 1)
                    parse_sse_chunk(part + "\n\n", timeline)
            if buf.strip():
                parse_sse_chunk(buf, timeline)
    except urllib.error.HTTPError as exc:
        print(f"HTTPError {exc.code}: {exc.read()[:500].decode('utf-8', errors='replace')}")
        return 2
    except Exception as exc:
        print(f"FAILED {type(exc).__name__}: {exc}")
        return 3

    total = time.perf_counter() - t0
    print(f"\n=== timeline ({len(timeline)} events) ===")
    for rel, pct, msg in [
        (ev[0] - t0, ev[1], ev[2]) for ev in timeline if ev[1] >= 0
    ]:
        print(f"  +{rel:7.1f}s  {pct:3d}%  {msg[:100]}")
    print(f"\nTOTAL_SECONDS={total:.1f}")
    done = any(pct == 100 or evt[1] == 100 for evt in timeline)
    errors = [evt for evt in timeline if evt[1] == -2]
    if errors:
        return 4
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
