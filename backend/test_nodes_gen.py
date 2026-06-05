import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from llm import chat_json
from prompts import build_nodes_system, build_nodes_user


async def main() -> None:
    bible = {
        "title": "雨夜重逢",
        "synopsis": "编辑林晚在雨夜咖啡馆遇见初恋陈屿，旧情与误会再次交织。",
        "setting": "现代都市",
        "tone": "浪漫暧昧",
        "characters": [{"name": "林晚", "role": "女主", "trait": "理性克制"}],
        "themes": ["重逢", "信任"],
        "key_events": ["咖啡馆偶遇", "坦白过往"],
        "plot_beats": ["雨夜进店", "四目相对", "回忆闪回", "误会解开", "拥抱结局"],
    }
    for max_t in (4096, 6144, 8192):
        print(f"trying max_tokens={max_t}...")
        try:
            raw = await chat_json(
                build_nodes_system(),
                build_nodes_user(bible, "urban_romance", source_char_count=2000),
                temperature=0.78,
                max_tokens=max_t,
            )
            nodes = raw.get("nodes") or {}
            print("SUCCESS max_tokens", max_t, "nodes", len(nodes))
            return
        except Exception as exc:
            print("FAIL max_tokens", max_t, type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
