"""Diagnose production /api/create/stream SSE."""
import json
import sys
import urllib.error
import urllib.request

TEXT = (
    "在一个遥远的仙侠世界里，少年林风自幼失去双亲，被青云门长老收养。他天赋平平，却有一颗不屈的心。"
    "某日，他在后山修炼时，意外发现一枚古老的玉佩。玉佩中传来神秘声音，指引他前往禁地寻找失落的剑诀。"
    "林风不顾同门劝阻，独自闯入禁地。在那里，他遇到了被封印千年的剑灵，也揭开了自己身世的秘密。"
    "原来，他的血脉中流淌着上古剑仙的力量。从此，林风踏上了一条充满抉择的修行之路——是守护门派，还是追寻真相？"
    "每一个选择，都将改变他的命运，也将影响整个修仙界的格局。"
) * 2

PAYLOAD = json.dumps({"text": TEXT, "style": "xianxia"}, ensure_ascii=False).encode("utf-8")


def parse_events(raw: bytes):
    events = []
    buf = raw
    while b"\n\n" in buf:
        part, buf = buf.split(b"\n\n", 1)
        evt = "unknown"
        data = ""
        for line in part.decode("utf-8", errors="replace").split("\n"):
            if line.startswith("event:"):
                evt = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].strip()
        if data:
            events.append((evt, data))
    if buf.strip():
        events.append(("trailing", buf.decode("utf-8", errors="replace")[:500]))
    return events


def test_stream(name: str, url: str) -> int:
    print(f"\n=== {name} ===")
    print(f"URL: {url}")
    req = urllib.request.Request(
        url,
        data=PAYLOAD,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            ct = resp.headers.get("Content-Type", "")
            print(f"HTTP {resp.status} Content-Type: {ct}")
            body = resp.read()
            print(f"Body bytes: {len(body)}")
            events = parse_events(body)
            types = [e[0] for e in events]
            print(f"Events ({len(events)}): {types}")
            for evt, data in events:
                if evt in ("error", "done", "trailing"):
                    print(f"  [{evt}] {data[:400]}")
            if "done" in types:
                return 0
            if "error" in types:
                return 2
            return 1
    except urllib.error.HTTPError as exc:
        print(f"HTTPError {exc.code}: {exc.read()[:500]}")
        return 3
    except Exception as exc:
        print(f"FAILED {type(exc).__name__}: {exc}")
        return 4


def test_health(url: str):
    print(f"\n--- health {url} ---")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"health failed: {exc}")


if __name__ == "__main__":
    test_health("https://2711editor.netlify.app/api/health")
    test_health("https://two711-editor-api.onrender.com/api/health")
    rc1 = test_stream("Netlify proxy", "https://2711editor.netlify.app/api/create/stream")
    rc2 = test_stream("Render direct", "https://two711-editor-api.onrender.com/api/create/stream")
    sys.exit(max(rc1, rc2))
