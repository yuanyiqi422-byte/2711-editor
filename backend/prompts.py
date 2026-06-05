from models import STYLE_LABELS, StylePreset


STYLE_GUIDES: dict[str, str] = {
    "xianxia": (
        "古风仙侠/玄幻：云海仙山、灵根、宗门、秘境试炼。画面偏水墨青绿、金霞、剑光。"
        "对白可文雅带江湖气，每句须交代情境与人物动机，忠于原文情节节奏。"
        "选项涉及拜师、夺宝、情义、逆天改命。"
    ),
    "urban_romance": (
        "都市言情/现代恋爱：写字楼、咖啡馆、雨夜街灯、豪门或职场。画面偏暖色柔光、都市夜景。"
        "对白贴近生活、有暧昧与误会，写清人物关系与情绪转折，勿缩成碎片短句。"
        "选项涉及表白、信任、事业与感情的取舍。"
    ),
    "mystery": (
        "悬疑推理：密室、旧案卷宗、雨夜追踪、反转线索。画面偏冷灰蓝、霓虹倒影、档案室灯光。"
        "对白克制、留悬念，但每句仍须推进线索或点明前因后果，保留关键信息。"
        "选项涉及调查、对质、隐瞒真相或冒险揭穿。"
    ),
    "campus": (
        "校园青春：教室走廊、社团、操场、毕业季。画面偏明亮日系、樱花或梧桐、午后阳光。"
        "对白青春口语、有悸动与成长，叙述清楚场景与人物心理，服务原著故事线。"
        "选项涉及友情、暗恋、竞赛、和解与告别。"
    ),
}


def narrative_scale(source_char_count: int) -> dict[str, int | str]:
    """按原文篇幅缩放圣经与节点密度目标。"""
    if source_char_count > 80_000:
        return {
            "tier": "长篇",
            "nodes_range": "15-25",
            "nodes_min": 15,
            "nodes_max": 25,
            "plot_beats_range": "8-12",
            "plot_beats_min": 8,
            "key_events_range": "5-8",
            "lines_per_scene": "3-6",
            "coverage": (
                "原文为长篇（>8万字）。必须将 plot_beats 与场景节点对齐采样章节中的主要情节点，"
                "覆盖开端、发展、高潮、收束各阶段；不要压缩成几个梗概场景，让玩家感受到完整故事弧。"
            ),
        }
    if source_char_count > 30_000:
        return {
            "tier": "中篇",
            "nodes_range": "10-15",
            "nodes_min": 10,
            "nodes_max": 15,
            "plot_beats_range": "6-10",
            "plot_beats_min": 6,
            "key_events_range": "4-6",
            "lines_per_scene": "3-5",
            "coverage": (
                "原文为中篇。场景须覆盖圣经中每条 plot_beat 的关键转折，"
                "勿把多章内容合并成单一过渡场景。"
            ),
        }
    return {
        "tier": "短篇",
        "nodes_range": "8-12",
        "nodes_min": 8,
        "nodes_max": 12,
        "plot_beats_range": "4-8",
        "plot_beats_min": 4,
        "key_events_range": "3-5",
        "lines_per_scene": "2-5",
        "coverage": "原文为短篇。仍须写清起承转合，每场景推进至少一个情节节拍。",
    }


def build_bible_system() -> str:
    return (
        "你是资深叙事设计师，擅长把小说/故事提炼为橙光式互动视觉小说大纲。"
        "只输出合法 JSON，不要 markdown。"
    )


def build_bible_user(text: str, style: StylePreset, source_char_count: int = 0) -> str:
    label = STYLE_LABELS[style]
    guide = STYLE_GUIDES[style]
    scale = narrative_scale(source_char_count or len(text))
    sampled_note = ""
    if source_char_count and source_char_count > len(text):
        sampled_note = (
            f"\n【篇幅说明】用户原文共约 {source_char_count:,} 字，以下为智能采样后的节选（{len(text):,} 字）。"
            "提炼时须覆盖采样中各章的主要冲突与转折，勿只写开头梗概。"
        )
    bible_text_limit = min(len(text), 80_000)
    return f"""阅读以下故事文本，提炼互动游戏用的故事圣经。
视觉风格 preset：{label}
风格指引：{guide}
篇幅档位：{scale["tier"]}（原文约 {source_char_count or len(text):,} 字）{sampled_note}

【原文】（可能为节选）
{text[:bible_text_limit]}

输出 JSON 格式：
{{
  "title": "游戏标题（8字内优先）",
  "synopsis": "100-180字梗概，保留主线冲突与结局走向",
  "setting": "时代与地点",
  "tone": "整体氛围",
  "characters": [{{"name":"", "role":"", "trait":""}}],
  "themes": ["主题1","主题2"],
  "key_events": ["可戏剧化事件1","事件2"],
  "plot_beats": ["关键情节节拍：含前因后果、人物动机、转折信息1","节拍2"]
}}

要求：
- 人物不超过6个；key_events {scale["key_events_range"]} 条。
- plot_beats {scale["plot_beats_range"]} 条：每条 25-70 字，写清「谁、在什么情境、做了什么、导致什么」，供后续剧本逐条扩写。
- {scale["coverage"]}
- 禁止只列人名地名或一句带过整卷剧情。"""


def build_nodes_system() -> str:
    return (
        "你是橙光/乙女向视觉小说编剧。按「场景→多句叙事对白→偶尔选项」结构写剧本。"
        "忠于原文情节与情绪，每句对白要有足够信息量，交代清楚前因后果，不要碎成口水短句。"
        "玩家大部分时候点击屏幕仅翻下一句，不是每句都要做选择。"
        "只输出合法 JSON。"
    )


def build_nodes_user(
    bible: dict,
    style: StylePreset,
    source_char_count: int = 0,
) -> str:
    label = STYLE_LABELS[style]
    guide = STYLE_GUIDES[style]
    scale = narrative_scale(source_char_count)
    import json

    bible_json = json.dumps(bible, ensure_ascii=False, indent=2)
    beats = bible.get("plot_beats") or []
    beat_hint = ""
    if beats:
        beat_hint = (
            f"\n【情节节拍】共 {len(beats)} 条，须为每条 plot_beat 安排至少一个对应场景（可合并相邻弱节拍，"
            f"但不得跳过高潮与结局）。目标场景数 {scale['nodes_range']} 个。"
        )
    return f"""根据故事圣经，生成橙光式可玩剧本（{scale["nodes_range"]} 个场景节点，2-3 个结局）。

视觉风格：{label}
风格指引：{guide}
篇幅档位：{scale["tier"]}（原文约 {source_char_count:,} 字）{beat_hint}

【故事圣经】
{bible_json}

输出 JSON：
{{
  "title": "游戏标题",
  "synopsis": "一句话",
  "start_node_id": "start",
  "nodes": {{
    "start": {{
      "id": "start",
      "title": "场景名（地点或事件）",
      "mood": "dark_mystery|neon_rain|golden_dawn|storm_sea|neutral",
      "image_prompt": "英文场景绘画提示，20-40词，无文字水印",
      "lines": [
        {{"speaker":"旁白","text":"叙事对白一句，24-80汉字，交代情境与因果","portrait":"none"}},
        {{"speaker":"角色名","text":"角色台词或心理，同样24-80字，保留关键信息与情绪","portrait":"left"}}
      ],
      "after_lines_next": "下一场景id",
      "choices": [],
      "is_ending": false,
      "ending_type": ""
    }},
    "branch_point": {{
      "id": "branch_point",
      "title": "抉择场景",
      "mood": "dark_mystery",
      "image_prompt": "...",
      "lines": [
        {{"speaker":"旁白","text":"铺垫句。","portrait":"none"}},
        {{"speaker":"你","text":"内心独白一句。","portrait":"right"}}
      ],
      "after_lines_next": "",
      "choices": [
        {{"id":"c1","text":"选项文案","next":"node_a","consequence_hint":""}},
        {{"id":"c2","text":"选项文案","next":"node_b","consequence_hint":""}}
      ],
      "is_ending": false,
      "ending_type": ""
    }}
  }}
}}

【橙光结构硬性规则】
1. 每个节点是一个「场景」，有独立 image_prompt 对应画面氛围。
2. lines：每场景 {scale["lines_per_scene"]} 句，每句 24-80 汉字（至少 15 字，勿超 90 字）。忠于 story bible / plot_beats，写清情境、人物动机与情绪，禁止拆成 10 字以内的碎句。可写对白、旁白、心理活动。
3. 约 60% 节点：lines 播完后用 after_lines_next 自动进入下一场景，choices 为空数组。
4. 约 40% 节点：关键抉择点，lines 播完后展示 2-3 个 choices，after_lines_next 留空。
5. 结局节点：is_ending=true，ending_type 为 good/bad/neutral，choices 空，after_lines_next 空，lines 2-4 句收束（每句仍须 24-80 字、交代结局因果）。
6. 所有 next / after_lines_next 必须指向已定义节点 id。
7. portrait：旁白用 none；NPC 常用 left；玩家「你」常用 right。
8. narrative 字段可留空，内容全部放进 lines。
9. 至少 2 个结局、剧情连贯，人物称呼一致。
10. {scale["coverage"]}
11. 场景总数须在 {scale["nodes_range"]} 范围内，不得因篇幅压缩而只写 5-8 个泛化场景。"""


def build_graph_outline_system() -> str:
    return (
        "你是橙光式视觉小说关卡设计师。先规划场景图谱骨架（不含对白 lines）。"
        "只输出合法 JSON。"
    )


def build_graph_outline_user(
    bible: dict,
    style: StylePreset,
    source_char_count: int = 0,
) -> str:
    import json

    scale = narrative_scale(source_char_count)
    label = STYLE_LABELS[style]
    guide = STYLE_GUIDES[style]
    bible_json = json.dumps(bible, ensure_ascii=False, indent=2)
    return f"""根据故事圣经，规划 {scale["nodes_range"]} 个场景节点的图谱骨架。

视觉风格：{label}
风格指引：{guide}
篇幅档位：{scale["tier"]}（原文约 {source_char_count:,} 字）

【故事圣经】
{bible_json}

输出 JSON（不要 lines 字段）：
{{
  "title": "游戏标题",
  "synopsis": "一句话",
  "start_node_id": "start",
  "nodes": {{
    "start": {{
      "id": "start",
      "title": "场景名",
      "mood": "neutral",
      "image_prompt": "english watercolor scene, 15-30 words",
      "after_lines_next": "scene_2",
      "choices": [],
      "is_ending": false,
      "ending_type": ""
    }},
    "branch_1": {{
      "id": "branch_1",
      "title": "抉择",
      "mood": "neutral",
      "image_prompt": "...",
      "after_lines_next": "",
      "choices": [
        {{"id":"c1","text":"选项A","next":"path_a","consequence_hint":""}},
        {{"id":"c2","text":"选项B","next":"path_b","consequence_hint":""}}
      ],
      "is_ending": false,
      "ending_type": ""
    }}
  }}
}}

规则：
- 场景数 {scale["nodes_range"]}；约 60% 用 after_lines_next，40% 用 choices。
- 至少 2 个结局（is_ending=true，choices 空，after_lines_next 空）。
- 所有 next / after_lines_next 必须指向已定义 id。
- 覆盖 plot_beats 的主要节拍，勿跳过高潮与结局。"""


def build_nodes_batch_system() -> str:
    return (
        "你是橙光视觉小说编剧。为已有图谱骨架节点补充多句对白 lines。"
        "每句 24-80 汉字，忠于圣经。只输出合法 JSON。"
    )


def build_nodes_batch_user(
    bible: dict,
    style: StylePreset,
    skeleton_nodes: dict,
    batch_ids: list[str],
    source_char_count: int = 0,
) -> str:
    import json

    scale = narrative_scale(source_char_count)
    label = STYLE_LABELS[style]
    subset = {nid: skeleton_nodes[nid] for nid in batch_ids if nid in skeleton_nodes}
    return f"""为以下场景节点补充对白 lines（本批 id：{", ".join(batch_ids)}）。

视觉风格：{label}
每场景 {scale["lines_per_scene"]} 句，每句 24-80 汉字。

【故事圣经摘要】
title: {bible.get("title", "")}
synopsis: {bible.get("synopsis", "")}

【本批节点骨架】
{json.dumps(subset, ensure_ascii=False, indent=2)}

输出 JSON：
{{
  "nodes": {{
    "node_id": {{
      ...原骨架字段保留...,
      "lines": [
        {{"speaker":"旁白","text":"24-80字叙事","portrait":"none"}},
        {{"speaker":"角色名","text":"对白","portrait":"left"}}
      ]
    }}
  }}
}}

不要修改 choices / after_lines_next / is_ending。不要新增或删除节点 id。"""


def build_expand_system() -> str:
    return (
        "你是橙光视觉小说编剧，续写叙事对白场景。每句 24-80 汉字，忠于原文情节与 bible，"
        "交代前因后果，勿缩成碎短句。保持 lines 多句点击续播格式。只输出合法 JSON。"
    )


def build_expand_user(req_text: str, style: StylePreset, game: dict, node_id: str, choice_id: str) -> str:
    label = STYLE_LABELS[style]
    import json

    game_json = json.dumps(game, ensure_ascii=False, indent=2)
    return f"""玩家选择了分支，请续写 2-4 个新场景节点（橙光格式）。

原文参考：
{req_text[:20000]}

风格：{label}
当前节点：{node_id}，选项：{choice_id}

【已有游戏】
{game_json}

输出 JSON：
{{
  "nodes": {{ "新id": {{ 同 StoryNode 结构，含 lines、image_prompt }} }},
  "updated_links": [{{"from_node":"","choice_id":"","next":""}}]
}}

新节点 lines：每场景 3-5 句，每句 24-80 汉字，保留关键剧情信息与情绪；至少 1 个结局节点。不要重复已有 id。"""
