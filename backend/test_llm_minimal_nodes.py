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
    user = """Generate JSON with 3 scene nodes for a romance VN:
{"title":"test","start_node_id":"start","nodes":{"start":{"id":"start","title":"cafe","mood":"neutral","image_prompt":"rainy cafe","lines":[{"speaker":"旁白","text":"雨夜。","portrait":"none"}],"after_lines_next":"end","choices":[],"is_ending":false},"end":{"id":"end","title":"end","mood":"neutral","image_prompt":"sunset","lines":[{"speaker":"旁白","text":"完。","portrait":"none"}],"after_lines_next":"","choices":[],"is_ending":true,"ending_type":"good"}}}
Only JSON."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Output JSON only."},
            {"role": "user", "content": user},
        ],
        "max_tokens": 2048,
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
    }
    timeout = httpx.Timeout(300.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
    print("status", resp.status_code)
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content") or msg.get("reasoning_content") or ""
    print("content len", len(content))
    print(content[:500])


if __name__ == "__main__":
    asyncio.run(main())
