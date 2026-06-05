"""End-to-end test: POST /api/create/stream until done or error."""
import asyncio
import json
import sys
import urllib.error
import urllib.request

TEXT = ("林晚是出版社编辑，雨夜在街角咖啡馆遇见多年未见的初恋陈屿，两人相对无言，回忆涌上心头。" * 12)


def main() -> int:
    url = "http://127.0.0.1:8010/api/create/stream"
    payload = json.dumps({"text": TEXT, "style": "urban_romance"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            buf = ""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buf:
                    part, buf = buf.split("\n\n", 1)
                    ev = "message"
                    data = ""
                    for line in part.split("\n"):
                        if line.startswith("event:"):
                            ev = line[6:].strip()
                        elif line.startswith("data:"):
                            data += line[5:].strip()
                    if not data:
                        continue
                    if ev == "status":
                        obj = json.loads(data)
                        print("status", obj.get("progress"), (obj.get("msg") or "")[:80])
                    elif ev == "error":
                        print("ERROR", data)
                        return 1
                    elif ev == "done":
                        obj = json.loads(data)
                        print("DONE nodes", len(obj.get("nodes") or {}), "title", obj.get("title"))
                        return 0
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read()[:300])
        return 1
    print("no done event")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
