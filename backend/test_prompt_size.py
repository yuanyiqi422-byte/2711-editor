import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    return json.loads(text[start : end + 1])


async def call(user: str, max_tokens: int = 4096) -> str:
    base = os.getenv("AI_API_BASE", "").rstrip("/")
    key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是视觉小说编剧。只输出合法 JSON。"},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.75,
        "stream": True,
        "response_format": {"type": "json_object"},
    }
    parts: list[str] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
        async with client.stream(
            "POST",
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                data = json.loads(chunk)
                parts.append(data["choices"][0].get("delta", {}).get("content") or "")
    return "".join(parts)


async def main() -> None:
    short = """根据圣经生成8个场景节点的橙光剧本 JSON。
圣经：{"title":"雨夜重逢","synopsis":"林晚雨夜咖啡馆遇见陈屿","plot_beats":["进店","对视","回忆","误会","和解","结局"]}
字段：title,start_node_id,nodes{{id,title,mood,image_prompt,lines[{{speaker,text,portrait}}],after_lines_next,choices,is_ending}}
每场景2-3句对白，每句24-60字。约60%自动after_lines_next，40%choices。2个结局。"""
    try:
        text = await call(short, 4096)
        raw = extract_json(text)
        print("short OK nodes", len(raw.get("nodes", {})))
    except Exception as exc:
        print("short FAIL", exc)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from prompts import build_nodes_system, build_nodes_user

    bible = {
        "title": "雨夜重逢",
        "synopsis": "林晚在雨夜咖啡馆遇见初恋陈屿。",
        "setting": "都市",
        "tone": "浪漫",
        "characters": [],
        "themes": [],
        "key_events": [],
        "plot_beats": ["雨夜", "对视", "回忆", "误会", "和解", "结局"],
    }
    long_user = build_nodes_user(bible, "urban_romance", 2000)
    print("long prompt chars", len(long_user))
    try:
        text = await call(long_user, 4096)
        raw = extract_json(text)
        print("long OK nodes", len(raw.get("nodes", {})))
    except Exception as exc:
        print("long FAIL", type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
