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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompts import build_nodes_system, build_nodes_user


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no json")


async def stream_completion(system: str, user: str, max_tokens: int, model: str | None = None) -> str:
    base = os.getenv("AI_API_BASE", "").rstrip("/")
    key = os.getenv("AI_API_KEY", "")
    model = model or os.getenv("AI_MODEL", "")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.78,
        "stream": True,
        "response_format": {"type": "json_object"},
    }
    timeout = httpx.Timeout(300.0, connect=30.0)
    parts: list[str] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise RuntimeError(body.decode()[:300])
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                data = json.loads(chunk)
                delta = data["choices"][0].get("delta", {})
                parts.append(delta.get("content") or "")
    return "".join(parts)


async def main() -> None:
    bible = {
        "title": "雨夜重逢",
        "synopsis": "编辑林晚在雨夜咖啡馆遇见初恋陈屿。",
        "setting": "现代都市",
        "tone": "浪漫",
        "characters": [{"name": "林晚", "role": "女主", "trait": "克制"}],
        "themes": ["重逢"],
        "key_events": ["偶遇"],
        "plot_beats": ["雨夜", "对视", "回忆", "误会", "和解", "结局"],
    }
    for m in (os.getenv("AI_MODEL", ""), "deepseek-chat"):
        print("model", m)
        try:
            text = await stream_completion(
                build_nodes_system(),
                build_nodes_user(bible, "urban_romance", source_char_count=2000),
                max_tokens=8192,
                model=m,
            )
            raw = extract_json(text)
            print("SUCCESS model", m, "nodes", len(raw.get("nodes", {})))
            return
        except Exception as exc:
            print("FAIL model", m, type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
