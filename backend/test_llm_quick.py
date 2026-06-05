import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


async def call(json_mode: bool, max_tokens: int = 8192) -> None:
    base = os.getenv("AI_API_BASE", "").rstrip("/")
    key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Output JSON only."},
            {"role": "user", "content": '{"ping": "generate minimal nodes"}'},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    timeout = httpx.Timeout(300.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
    print("json_mode", json_mode, "max_tokens", max_tokens, "status", resp.status_code)
    print(resp.text[:400])


if __name__ == "__main__":
    asyncio.run(call(True, 100))
    asyncio.run(call(False, 100))
