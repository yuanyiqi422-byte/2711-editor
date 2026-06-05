import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


async def main() -> None:
    base = os.getenv("AI_API_BASE", "").rstrip("/")
    key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是助手。只输出合法 JSON，不要 markdown。"},
            {"role": "user", "content": '输出 {"hello":"world"}'},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    timeout = httpx.Timeout(300.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
    data = resp.json()
    msg = data["choices"][0]["message"]
    print(json.dumps(msg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
