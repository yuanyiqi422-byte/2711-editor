import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import chat_json, LLMError


async def gen_batch(batch_num: int, node_ids: list[str], bible: dict) -> dict:
    user = f"""根据故事圣经，生成第 {batch_num} 批场景节点（仅这些 id：{', '.join(node_ids)}）。
圣经：{json.dumps(bible, ensure_ascii=False)}
输出 JSON：{{"nodes":{{"id":{{"id":"","title":"","mood":"neutral","image_prompt":"english scene","lines":[{{"speaker":"旁白","text":"24-60字对白","portrait":"none"}}],"after_lines_next":"","choices":[],"is_ending":false}}}}}}
每节点 2-3 句 lines。抉择点含 2 choices。结局 is_ending true。"""
    return await chat_json(
        "你是视觉小说编剧。只输出 JSON。",
        user,
        temperature=0.75,
        max_tokens=4096,
    )


async def main() -> None:
    bible = {
        "title": "雨夜重逢",
        "synopsis": "林晚雨夜遇见陈屿",
        "plot_beats": ["进店", "对视", "回忆", "和解", "结局"],
    }
    batches = [
        ["start", "scene_2", "scene_3", "branch_1"],
        ["scene_4", "scene_5", "ending_good", "ending_bad"],
    ]
    all_nodes = {}
    for i, ids in enumerate(batches, 1):
        try:
            raw = await gen_batch(i, ids, bible)
            nodes = raw.get("nodes") or {}
            all_nodes.update(nodes)
            print("batch", i, "ok", len(nodes))
        except LLMError as exc:
            print("batch", i, "fail", exc)
            return
    print("total nodes", len(all_nodes))


if __name__ == "__main__":
    asyncio.run(main())
