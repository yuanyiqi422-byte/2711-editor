"""场景类型与对白句数目标。"""

from __future__ import annotations

SCENE_TYPE_GUIDE = """
【场景类型配比】全剧须覆盖以下类型（约占比）：
- intro（开场铺垫）≈10%：每场景 4–6 句，情绪平稳
- buildup（矛盾积累）≈25%：每场景 6–8 句，有小冲突
- climax（高潮对抗）≈20%：每场景 10–15 句，强对白
- resolution（情感落定）≈20%：每场景 6–10 句，有余韵
- interlude（过渡插曲）≈15%：每场景 4–6 句，呼吸感
- ending（结局）≈10%：每场景 8–14 句，有总结感
每个节点必须含 scene_type（上述之一）；结局节点 scene_type=ending。
"""

SCENE_TYPE_LINES: dict[str, tuple[int, int]] = {
    "intro": (4, 6),
    "buildup": (6, 8),
    "climax": (10, 15),
    "resolution": (6, 10),
    "interlude": (4, 6),
    "ending": (8, 14),
}


def lines_target_for_scene_type(scene_type: str) -> str:
    st = (scene_type or "buildup").strip().lower()
    lo, hi = SCENE_TYPE_LINES.get(st, SCENE_TYPE_LINES["buildup"])
    return f"{lo}-{hi}"
