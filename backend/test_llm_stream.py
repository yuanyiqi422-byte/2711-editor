import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


async def try_request(use_stream: bool, json_mode: bool, model_override: str | None = None) -> None:
    base = os.getenv("AI_API_BASE", "").rstrip("/")
    key = os.getenv("AI_API_KEY", "")
    model = model_override or os.getenv("AI_MODEL", "")
    user = 'Output JSON: {"nodes":{"a":{"id":"a","lines":[{"speaker":"旁白","text":"测试一句足够长的对白内容在这里","portrait":"none"}],"choices":[]}}}'
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Output JSON only, no markdown."},
            {"role": "user", "content": user},
        ],
        "max_tokens": 1024,
        "temperature": 0.5,
        "stream": use_stream,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    timeout = httpx.Timeout(300.0, connect=30.0)
    label = f"stream={use_stream} json={json_mode} model={model}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if use_stream:
                parts = []
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
                        delta = data["choices"][0].get("delta", {})
                        parts.append(delta.get("content") or delta.get("reasoning_content") or "")
                text = "".join(parts)
                print("OK", label, "len", len(text), text[:120])
            else:
                resp = await client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json=payload,
                )
                data = resp.json()
                msg = data["choices"][0]["message"]
                text = msg.get("content") or msg.get("reasoning_content") or ""
                print("OK", label, "status", resp.status_code, "len", len(text), text[:120])
    except Exception as exc:
        print("FAIL", label, type(exc).__name__, exc)


async def main() -> None:
    await try_request(False, True)
    await try_request(False, False)
    await try_request(True, False)
    await try_request(True, True)
    for alt in ("deepseek-chat", "deepseek-reasoner"):
        await try_request(True, False, alt)


if __name__ == "__main__":
    asyncio.run(main())
