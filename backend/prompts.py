from models import STYLE_LABELS, StylePreset
from scene_types import SCENE_TYPE_GUIDE, lines_target_for_scene_type
from source_context import PER_NODE_EXCERPT_CHARS, truncate_node_context


FAITHFULNESS_RULE = (
    "必须忠实于原文情节，保留关键人物、冲突、转折与细节，禁止泛泛而谈或跳过重要段落；"
    "不得压缩为梗概式场景，每场景对白须承接原文细节、人物语气与因果链，"
    "让玩家通过点击对白逐步经历完整故事而非读摘要。"
)

DIALOGUE_QUOTE_RULE = (
    "对白与旁白中引用中文话语时优先使用「」引号（也可用全角“”），"
    "勿用英文单引号 ' 或 ASCII 双引号 \" 包裹中文台词；"
    "英文专名、缩写中的撇号（如 O'Brien、don't、McDonald's）保留原样。"
)

STYLE_GUIDES: dict[str, str] = {
    "xianxia": (
        "古风仙侠/玄幻：云海仙山、灵根、宗门、秘境试炼。画面偏水墨青绿、金霞、剑光。"
        "对白可文雅带江湖气，每句须交代情境与人物动机，忠于原文情节节奏。"
        "选项涉及拜师、夺宝、情义、逆天改命。"
        + FAITHFULNESS_RULE
    ),
    "urban_romance": (
        "都市言情/现代恋爱：写字楼、咖啡馆、雨夜街灯、豪门或职场。画面偏暖色柔光、都市夜景。"
        "对白贴近生活、有暧昧与误会，写清人物关系与情绪转折，勿缩成碎片短句。"
        "选项涉及表白、信任、事业与感情的取舍。"
        + FAITHFULNESS_RULE
    ),
    "mystery": (
        "悬疑推理：密室、旧案卷宗、雨夜追踪、反转线索。画面偏冷灰蓝、霓虹倒影、档案室灯光。"
        "对白克制、留悬念，但每句仍须推进线索或点明前因后果，保留关键信息。"
        "选项涉及调查、对质、隐瞒真相或冒险揭穿。"
        + FAITHFULNESS_RULE
    ),
    "campus": (
        "校园青春：教室走廊、社团、操场、毕业季。画面偏明亮日系、樱花或梧桐、午后阳光。"
        "对白青春口语、有悸动与成长，叙述清楚场景与人物心理，服务原著故事线。"
        "选项涉及友情、暗恋、竞赛、和解与告别。"
        + FAITHFULNESS_RULE
    ),
}


def narrative_quality_floor(source_char_count: int) -> dict[str, int]:
    """速度优化不得突破的密度下限（快路径 / 节拍骨架亦须满足）。"""
    chars = max(int(source_char_count or 0), 0)
    if chars >= 18_000:
        return {"nodes_min": 14, "endings_min": 3, "min_choice_moments": 5}
    if chars >= 8000:
        return {"nodes_min": 12, "endings_min": 3, "min_choice_moments": 4}
    if chars >= 1500:
        return {"nodes_min": 6, "endings_min": 3, "min_choice_moments": 3}
    return {"nodes_min": 5, "endings_min": 3, "min_choice_moments": 2}


def narrative_scale(source_char_count: int) -> dict[str, int | str]:
    """按原文字数缩放密度；短文本少节点快完成，长文本封顶避免批次数爆炸。"""
    chars = max(int(source_char_count or 0), 0)
    if chars <= 0:
        chars = 500

    min_total_lines = max(12, min(900, int(chars * 1.5 / 1000)))
    max_total_lines = max(min_total_lines + 8, min(900, int(chars * 2.2 / 1000)))

    if chars < 1500:
        nodes_min = max(5, min(8, 4 + chars // 200))
        nodes_max = nodes_min + 3
        choice_min = max(2, min(4, nodes_min // 2 + 1))
        plot_beats_min = max(3, min(6, chars // 250 + 2))
    elif chars <= 5500:
        nodes_min = max(6, min(10, chars // 650 + 3))
        nodes_max = max(nodes_min + 2, min(12, chars // 550 + 4))
        choice_min = max(2, min(5, nodes_min // 2))
        plot_beats_min = max(4, min(8, chars // 900 + 3))
    elif chars < 8000:
        nodes_min = max(7, min(12, chars // 700 + 3))
        nodes_max = max(nodes_min + 2, min(14, chars // 600 + 5))
        choice_min = max(3, min(6, nodes_min // 2))
        plot_beats_min = max(5, min(10, chars // 1100 + 3))
    elif chars <= 22_000:
        nodes_min = max(12, min(18, chars // 2500 + 6))
        nodes_max = max(nodes_min + 2, min(18, chars // 2000 + 6))
        choice_min = max(4, min(8, nodes_min // 3))
        plot_beats_min = max(6, min(12, chars // 3500 + 4))
    elif chars < 30_000:
        nodes_min = max(14, min(22, chars // 1800 + 8))
        nodes_max = max(nodes_min + 3, min(26, chars // 1500 + 10))
        choice_min = max(5, min(10, nodes_min // 3))
        plot_beats_min = max(6, min(14, chars // 5000 + 4))
    else:
        nodes_min = max(18, min(40, chars // 2500 + 10))
        nodes_max = max(nodes_min + 5, min(50, chars // 2000 + 12))
        choice_min = max(8, min(20, nodes_min // 3))
        plot_beats_min = max(8, min(18, chars // 8000 + 4))

    plot_beats_max = max(plot_beats_min + 2, min(18, plot_beats_min + max(chars // 12_000, 1) + 1))

    if chars > 80_000:
        tier = "长篇"
    elif chars > 30_000:
        tier = "中篇"
    else:
        tier = "短篇"

    endings_min = 3

    floor = narrative_quality_floor(chars)
    nodes_min = max(nodes_min, floor["nodes_min"])
    nodes_max = max(nodes_max, nodes_min + 2)
    endings_min = max(endings_min, floor["endings_min"])
    choice_min = max(choice_min, floor["min_choice_moments"])

    density = {
        "tier": tier,
        "nodes_range": f"{nodes_min}-{nodes_max}",
        "nodes_min": nodes_min,
        "nodes_max": nodes_max,
        "plot_beats_range": f"{plot_beats_min}-{plot_beats_max}",
        "plot_beats_min": plot_beats_min,
        "key_events_range": "6-12" if tier == "长篇" else "5-10",
        "lines_per_scene": "4-15（按 scene_type）",
        "choices_per_branch": "2-4",
        "endings_range": "3-8" if tier == "长篇" else "3-6",
        "endings_min": endings_min,
        "min_total_lines": min_total_lines,
        "max_total_lines": max_total_lines,
        "min_choice_moments": choice_min,
        "choice_ratio": "35%-55%",
        "min_high_impact": max(2, choice_min // 4),
    }

    density["coverage"] = (
        f"原文约 {chars:,} 字（{tier}）。全剧可点击对白 {min_total_lines}–{max_total_lines} 句；"
        f"抉择时刻 {choice_min}–{min(65, choice_min + 15)} 次；场景 {nodes_min}–{nodes_max} 个。"
        "须覆盖开端/发展/高潮/收束，禁止梗概式带过。"
    )
    return density


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
    bible_text = text
    return f"""阅读以下故事文本，提炼互动游戏用的故事圣经。
视觉风格 preset：{label}
风格指引：{guide}
篇幅档位：{scale["tier"]}（原文约 {source_char_count or len(text):,} 字）{sampled_note}

【原文】
{bible_text}

输出 JSON 格式：
{{
  "title": "游戏标题（8字内优先）",
  "synopsis": "100-180字梗概，保留主线冲突与结局走向",
  "setting": "时代与地点",
  "tone": "整体氛围",
  "characters": [{{"name":"", "role":"", "trait":""}}],
  "themes": ["主题1","主题2"],
  "key_events": ["可戏剧化事件1","事件2"],
  "plot_beats": ["关键情节节拍：含前因后果、人物动机、转折信息1","节拍2"],
  "endings": [
    {{
      "id": "good_end",
      "label": "花好月圆",
      "trigger_logic": "须在场景 A 选择帮助某人 AND 在场景 C 揭露真相",
      "key_nodes": ["scene_007", "scene_021"],
      "tone": "温暖，有代价但值得"
    }},
    {{
      "id": "bad_end",
      "label": "孤岛",
      "trigger_logic": "场景 B 选择沉默 AND 场景 D 选择离开",
      "key_nodes": ["scene_012", "scene_028"],
      "tone": "寂寥，回避酿成遗憾"
    }},
    {{
      "id": "neutral_end",
      "label": "平淡收场",
      "trigger_logic": "关键抉择各取折中，未达圆满亦未彻底决裂",
      "key_nodes": ["scene_018", "scene_025"],
      "tone": "释然中带一丝遗憾"
    }}
  ],
  "emotional_curve": [
    {{"position": "全书10%", "mood": "期待", "note": "主角初登场"}},
    {{"position": "全书50%", "mood": "紧张", "note": "核心冲突爆发"}},
    {{"position": "全书85%", "mood": "释然或坠落", "note": "走向结局"}}
  ]
}}

要求：
- 人物 3–8 个；key_events {scale["key_events_range"]} 条。
- plot_beats {scale["plot_beats_range"]} 条：每条 25-70 字，写清「谁、在什么情境、做了什么、导致什么」。
- endings {scale["endings_range"]} 个：须含 good/bad/neutral 至少两种；trigger_logic 写清关键抉择组合，key_nodes 用占位 scene id。
- emotional_curve 5–10 个点，标记全书情绪起伏高低。
- {scale["coverage"]}
- 禁止只列人名地名或一句带过整卷剧情。"""


def build_nodes_system() -> str:
    return (
        "你是橙光/乙女向视觉小说编剧。按「场景→多句叙事对白→偶尔选项」结构写剧本。"
        + "忠于原文情节与情绪，每句对白要有足够信息量，交代清楚前因后果，不要碎成口水短句。"
        + "必须忠实于原文情节，保留关键人物、冲突、转折，禁止泛泛而谈或跳过重要段落；"
        + "不得压缩为梗概式场景，每场景对白须承接原文细节。"
        + "玩家大部分时候点击屏幕仅翻下一句，不是每句都要做选择。"
        + DIALOGUE_QUOTE_RULE
        + "只输出合法 JSON。"
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
    return f"""根据故事圣经，生成橙光式可玩剧本（至少 {scale["endings_min"]} 个互不相同的结局，{scale["endings_range"]} 个结局目标，{scale["nodes_range"]} 个场景节点）。

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
      "chapter": 1,
      "chapter_title": "第一章 · 开端",
      "chapter_blurb": "本章一句话引子，20-40字",
      "mood": "dark_mystery|neon_rain|golden_dawn|storm_sea|neutral",
      "image_prompt": "英文场景绘画提示，20-40词，纯背景空镜（no people, no UI overlay），含地点关键词如 cafeteria/palace/morgue/inn，无文字水印",
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
        {{"id":"c1","text":"选项文案（来自原文冲突）","next":"node_a","impact":"medium","immediate_consequence":"当场后果","narrative_impact":"影响后续关系","relationship_delta":"+1"}},
        {{"id":"c2","text":"另一立场","next":"node_b","impact":"high","immediate_consequence":"路线分叉","narrative_impact":"导向不同结局线","relationship_delta":"-1"}},
        {{"id":"c3","text":"缓和/观望","next":"node_c","impact":"low","immediate_consequence":"气氛变化","narrative_impact":"微调氛围","relationship_delta":"0"}}
      ],
      "is_ending": false,
      "ending_type": ""
    }}
  }}
}}

【橙光结构硬性规则】
0. 【密度下限】全剧 lines 合计不少于 {scale["min_total_lines"]} 句；至少 {scale["min_choice_moments"]} 个抉择时刻（choices 含 2-4 个选项的节点，禁止仅 1 个选项）。{scale["coverage"]}
1. 每个节点是一个「场景」，有独立 image_prompt 对应画面氛围。
2. lines：每场景 {scale["lines_per_scene"]} 句，每句 24-80 汉字（至少 15 字，勿超 90 字）。忠于 story bible / plot_beats 与原文细节，写清情境、人物动机与情绪，禁止拆成 10 字以内的碎句。可写对白、旁白、心理活动。禁止梗概式缩写。
3. 约 40% 节点：纯过渡，lines 播完后 after_lines_next 自动进入下一场景，choices 为空。连续自动过渡不得超过 4 个场景。
4. 约 60% 非结局节点应为抉择点：lines 播完后展示 {scale["choices_per_branch"]} 个 choices，after_lines_next 留空。选项 text 须为完整、可读的短句行动（如「追问项链下落」「沉默不语」「直接离开」「答应帮忙」「断然拒绝」），主谓齐全、禁止截断原文片段拼接；禁止括号附带后果；禁止「观望某某说」「介入某某说」及「徐徐图之」「围绕…图之」「三思后回应」「果断抉择」等模板套话。后果写 immediate_consequence，长线影响写 narrative_impact。同节点各 text 须互不相同。各选项 next 须不同，impact 须标注 low/medium/high：low=氛围/好感微调，medium=剧情波动，high=路线/结局分叉。全剧至少 {scale["min_high_impact"]} 个 impact=high 的选项。抉择时刻总数须 ≥{scale["min_choice_moments"]}。
5. 结局节点（硬性）：至少 {scale["endings_min"]} 个互不相同的结局（is_ending=true），ending_type 须含 good/bad/neutral 中至少两种（ending_type 仅填英文枚举 good/bad/neutral/true/hidden/open，供内部校验）；每个结局须有独立因果链与情感收束，让玩家有动力重玩收集全结局。choices 空，after_lines_next 空，lines 3-5 句收束（每句仍须 24-80 字、交代结局因果）。title 须为 4-12 字中文文学收束语（结局式、略带文采，如「尘埃落定，各归其所」「潮起潮落，故事至此」），禁止在 title 中写 good/bad/neutral 等英文 ending_type，也禁止写「好结局」「坏结局」「普通结局」「平和结局」等道德评判标签；对白引号优先用「」，勿用英文单引号 ' 或 ASCII 双引号。
6. 所有 next / after_lines_next 必须指向已定义节点 id。
7. portrait：旁白用 none；NPC 常用 left；玩家「你」常用 right。
8. narrative 字段可留空，内容全部放进 lines。
9. 空字符串字段一律用 ""，禁止输出 null（尤其 after_lines_next、ending_type、chapter_blurb）。
10. 结局数量不得少于 {scale["endings_min"]} 个；剧情连贯，人物称呼一致；主线（无分支直达结局的最短路径）至少 {max(scale["nodes_min"] // 2, 8)} 个场景。
11. {scale["coverage"]}
12. 场景总数须在 {scale["nodes_range"]} 范围内，不得因篇幅压缩而只写少量泛化场景；宁可多写过渡场景与对白，也不要跳过 bible 中的节拍。
13. 【章节】将全剧分为 3-5 章（chapter 从 1 递增）。每节点须含 chapter、chapter_title（如「第二章 · 雨夜追踪」）；每章第一个场景节点另填 chapter_blurb（20-40 字引子），同章其余节点 chapter_blurb 可留空。章节边界对齐 plot_beats 大转折，勿每场景一章。
14. 【引号】{DIALOGUE_QUOTE_RULE}"""


def _outline_retry_block(prior_errors: list[str] | None) -> str:
    if not prior_errors:
        return ""
    lines = "\n".join(f"- {e}" for e in prior_errors[:10])
    return f"\n\n【上轮骨架校验失败，必须修正】\n{lines}"


def build_graph_outline_system() -> str:
    return (
        "你是橙光式视觉小说关卡设计师。先规划场景图谱骨架（不含对白 lines）。"
        "只输出合法 JSON。"
    )


def compact_bible_for_outline(bible: dict) -> dict:
    """大纲阶段极简圣经：仅保留规划骨架所需字段。"""
    endings = bible.get("endings") or []
    compact_endings = []
    for e in endings:
        if not isinstance(e, dict):
            continue
        compact_endings.append(
            {
                "id": e.get("id"),
                "label": e.get("label"),
                "trigger_logic": (str(e.get("trigger_logic") or ""))[:120],
            }
        )
    chars = bible.get("characters") or []
    compact_chars = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        compact_chars.append({"name": c.get("name"), "role": c.get("role")})
    synopsis = str(bible.get("synopsis") or "")
    if len(synopsis) > 220:
        synopsis = synopsis[:220].rstrip() + "…"
    return {
        "title": bible.get("title"),
        "synopsis": synopsis,
        "characters": compact_chars,
        "key_events": (bible.get("key_events") or [])[:10],
        "plot_beats": bible.get("plot_beats") or [],
        "endings": compact_endings,
    }


def compact_bible_dict(bible: dict) -> dict:
    """大纲阶段用精简圣经，避免重复灌入已提炼字段。"""
    endings = bible.get("endings") or []
    compact_endings = []
    for e in endings:
        if not isinstance(e, dict):
            continue
        compact_endings.append(
            {
                "id": e.get("id"),
                "label": e.get("label"),
                "trigger_logic": e.get("trigger_logic"),
                "key_nodes": e.get("key_nodes"),
                "tone": e.get("tone"),
            }
        )
    chars = bible.get("characters") or []
    compact_chars = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        compact_chars.append(
            {
                "name": c.get("name"),
                "role": c.get("role"),
                "trait": c.get("trait"),
            }
        )
    return {
        "title": bible.get("title"),
        "synopsis": bible.get("synopsis"),
        "setting": bible.get("setting"),
        "tone": bible.get("tone"),
        "themes": bible.get("themes") or [],
        "characters": compact_chars,
        "key_events": bible.get("key_events") or [],
        "plot_beats": bible.get("plot_beats") or [],
        "endings": compact_endings,
        "emotional_curve": bible.get("emotional_curve") or [],
    }


def build_outline_source_sample(source_text: str, max_chars: int = 2000) -> str:
    """长篇原文节选：头尾采样，供大纲校准节奏（非全量灌入）。"""
    text = (source_text or "").strip()
    if not text or len(text) <= max_chars:
        return text
    head = int(max_chars * 0.55)
    tail = max_chars - head - 40
    return (
        text[:head].rstrip()
        + "\n\n⋯⋯（中段省略，圣经已覆盖主线）⋯⋯\n\n"
        + text[-tail:].lstrip()
    )


def build_graph_outline_user(
    bible: dict,
    style: StylePreset,
    source_char_count: int = 0,
    *,
    source_text: str = "",
    compact: bool = True,
    source_sample_chars: int = 2000,
    prior_errors: list[str] | None = None,
) -> str:
    import json

    scale = narrative_scale(source_char_count)
    label = STYLE_LABELS[style]
    guide = STYLE_GUIDES[style]
    bible_payload = (
        compact_bible_for_outline(bible)
        if compact
        else bible
    )
    bible_json = json.dumps(bible_payload, ensure_ascii=False, separators=(",", ":"))
    choice_max = min(65, scale["min_choice_moments"] + 15)
    sample_block = ""
    if compact and source_text.strip():
        sample = build_outline_source_sample(source_text, source_sample_chars)
        if sample:
            sample_block = (
                f"\n【原文采样（约 {len(sample):,} 字，圣经已提炼主线；大纲须对齐节拍与结局）】\n"
                f"{sample}\n"
            )
    return f"""根据故事圣经，规划 {scale["nodes_range"]} 个场景节点的图谱骨架。

视觉风格：{label}
风格指引：{guide}
篇幅档位：{scale["tier"]}（原文约 {source_char_count:,} 字）

【故事圣经】
{bible_json}
{sample_block}

输出 JSON（不要 lines 字段）：
{{
  "title": "游戏标题",
  "synopsis": "一句话",
  "start_node_id": "start",
  "nodes": {{
    "start": {{
      "id": "start",
      "title": "场景名",
      "chapter": 1,
      "chapter_title": "第一章 · 开端",
      "chapter_blurb": "本章引子 20-40 字",
      "scene_type": "intro",
      "mood": "neutral",
      "image_prompt": "english watercolor empty background, 15-30 words, location keywords, no people",
      "emotion_open": "困惑",
      "emotion_trigger": "发现关键线索",
      "emotion_close": "决心",
      "emotion_action": "主角决定追查",
      "after_lines_next": "scene_2",
      "choices": [],
      "is_ending": false,
      "ending_type": ""
    }},
    "branch_1": {{
      "id": "branch_1",
      "title": "抉择",
      "scene_type": "climax",
      "mood": "dark_mystery",
      "image_prompt": "...",
      "emotion_open": "紧张",
      "emotion_trigger": "必须当场选择",
      "emotion_close": "悬而未决",
      "emotion_action": "主角开口或沉默",
      "after_lines_next": "",
      "choices": [
        {{
          "id":"c1","text":"当面质问对方","next":"path_a","impact":"high",
          "immediate_consequence":"下一场直接呈现对质场面",
          "narrative_impact":"影响结局 good_end 与 scene_021",
          "relationship_delta":"林晓好感+1"
        }},
        {{
          "id":"c2","text":"选项B","next":"path_b","impact":"medium",
          "immediate_consequence":"对方转身离开，关系破裂",
          "narrative_impact":"导向 bad_end 分支",
          "relationship_delta":"林晓好感-1"
        }},
        {{
          "id":"c3","text":"选项C","next":"path_c","impact":"low",
          "immediate_consequence":"暂时缓和气氛",
          "narrative_impact":"微调后续对话语气",
          "relationship_delta":"林晓好感0"
        }}
      ],
      "is_ending": false,
      "ending_type": ""
    }}
  }}
}}

{SCENE_TYPE_GUIDE}

规则：
- 【密度】全剧对白目标 {scale["min_total_lines"]}–{scale["max_total_lines"]} 句；抉择时刻 {scale["min_choice_moments"]}–{choice_max} 次；{scale["coverage"]}
- 场景数 {scale["nodes_range"]}；约 {scale["choice_ratio"]} 非结局节点含 choices（2-4 项），其余用 after_lines_next 过渡；密度可略浮动，但须保证分支与结局可达。
- 每个非结局节点须含 scene_type 与 emotion_open/trigger/close/action 四字段。
- 每个 choices 项须含 impact（low/medium/high）、immediate_consequence、narrative_impact、relationship_delta。text 须为完整短句行动（如「当面质问」「沉默不语」「直接离开」「答应帮忙」「断然拒绝」），主谓齐全、禁止截断原文片段拼接；禁止「观望某某说」「介入某某说」及「徐徐图之」「围绕…图之」「三思后回应」「果断抉择」等模板；禁止在 text 中用括号附带后果/影响；后果写在 immediate_consequence，长线影响写在 narrative_impact。同节点各选项 text 须互不相同，禁止同义伪分支。
- 全剧至少 {scale["min_high_impact"]} 个 impact=high 选项，导向不同路线或结局；禁止整条主线无选项直达结局。
- 骨架须落实 bible.endings 的 trigger_logic，关键 key_nodes 须出现在图中。
- 至少 {scale["endings_min"]} 个结局节点（is_ending=true，互不相同的 ending_type，须含 good/bad/neutral 至少两种；ending_type 仅填英文枚举 good/bad/neutral/true/hidden/open）。title 须为 4-12 字中文文学收束语（结局式、略带文采），禁止 title 含 good/bad/neutral 等英文，也禁止「好结局」「坏结局」「普通结局」「平和结局」；从 start 可达至少一 good 与一 bad/neutral。禁止只写 1 个结局。
- 所有 next / after_lines_next 必须指向已定义 id。
- 【章节】全剧 5–10 章（长篇）或 3–5 章（短篇）；章节对齐 plot_beats 大转折。{_outline_retry_block(prior_errors)}"""


def build_nodes_batch_system() -> str:
    return (
        "你是橙光视觉小说编剧。为已有图谱骨架节点补充多句对白 lines。"
        + "每句 24-80 汉字，忠于圣经与原文情节细节；每场景须写足句数，勿缩成 1-2 句敷衍。"
        + "必须忠实于原文，禁止梗概式缩写或跳过关键转折。"
        + DIALOGUE_QUOTE_RULE
        + "【输出格式 — 硬性】只输出一个合法 JSON 对象，以 { 开头、以 } 结尾。"
        + "禁止任何前言、后记、解释、规划、Markdown 代码块或「我们先看 scene_x」类文字。"
        + "禁止输出思考过程；直接输出 JSON。"
    )


def build_nodes_batch_user(
    bible: dict,
    style: StylePreset,
    skeleton_nodes: dict,
    batch_ids: list[str],
    source_char_count: int = 0,
    node_source_context: dict[str, str] | None = None,
    prev_scene_lines: dict[str, str] | None = None,
) -> str:
    import json

    scale = narrative_scale(source_char_count)
    label = STYLE_LABELS[style]
    subset = compact_skeleton_for_batch(skeleton_nodes, batch_ids)
    has_node_context = bool(
        node_source_context and any(str(v).strip() for v in node_source_context.values())
    )
    beats = bible.get("plot_beats") or []
    beats_block = ""
    if beats and not has_node_context:
        beats_block = "【全剧情节节拍 plot_beats】\n" + "\n".join(
            f"{i + 1}. {b}" for i, b in enumerate(beats) if b
        ) + "\n\n"

    context_blocks: list[str] = []
    for nid in batch_ids:
        raw = subset.get(nid) or {}
        title = raw.get("title") or nid
        st = raw.get("scene_type") or "buildup"
        line_target = lines_target_for_scene_type(st)
        parts = [f"--- 场景 {nid}（{title}）scene_type={st}，目标 {line_target} 句 ---"]
        ctx = truncate_node_context(
            (node_source_context or {}).get(nid, "").strip(),
            PER_NODE_EXCERPT_CHARS,
        )
        if ctx:
            parts.append(ctx)
        arc = _format_emotion_arc(raw)
        if arc:
            parts.append(arc)
        prev = (prev_scene_lines or {}).get(nid, "").strip()
        if prev:
            parts.append("【上一场景末 2 句（须自然衔接）】\n" + prev)
        context_blocks.append("\n".join(parts))

    source_block = ""
    if context_blocks:
        source_block = "【本批各场景写作上下文】\n" + "\n\n".join(context_blocks) + "\n\n"

    return f"""为以下场景节点补充对白 lines（本批 id：{", ".join(batch_ids)}）。

视觉风格：{label}
每场景句数须符合 skeleton 中 scene_type 的目标区间（见下方上下文）。全剧目标 {scale["min_total_lines"]}–{scale["max_total_lines"]} 句。
必须忠实于原文节选与情感弧，保留人物语气、细节与因果，禁止梗概式缩写。

【故事圣经摘要】
title: {bible.get("title", "")}
synopsis: {bible.get("synopsis", "")}

{beats_block}{source_block}【本批节点骨架】
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

【choices 硬性保留】若骨架节点含 choices（2-4 项），输出时必须原样保留 id/next/impact/immediate_consequence/narrative_impact/relationship_delta，禁止清空或删减。text 须结合该节点 title/情节节拍写完整短句行动（如「追问项链下落」「沉默不语」「直接离开」「答应帮忙」「断然拒绝」），主谓齐全、禁止截断原文片段拼接；禁止「观望某某说」「介入某某说」及「徐徐图之」「围绕…图之」「三思后回应」「果断抉择」等全剧模板；勿把 immediate_consequence 或 narrative_impact 塞进 text 或括号后缀。同节点各 text 须互不相同。
不要修改 after_lines_next / is_ending / scene_type / emotion_*。不要新增或删除节点 id。

【再次强调】你的回复必须是且仅是上述 JSON 对象：不要解释、不要规划、不要 Markdown、不要「我们根据…为 scene_x 补充」等文字。只输出 JSON。"""


_SKELETON_BATCH_KEYS = (
    "id",
    "title",
    "scene_type",
    "chapter",
    "chapter_title",
    "chapter_blurb",
    "mood",
    "emotion_open",
    "emotion_trigger",
    "emotion_close",
    "emotion_action",
    "after_lines_next",
    "choices",
    "is_ending",
    "ending_type",
)


def compact_skeleton_for_batch(skeleton_nodes: dict, batch_ids: list[str]) -> dict:
    """场景批量阶段只保留写对白需要的骨架字段，缩小 prompt。"""
    compact: dict[str, dict] = {}
    for nid in batch_ids:
        raw = skeleton_nodes.get(nid)
        if not isinstance(raw, dict):
            continue
        item = {k: raw[k] for k in _SKELETON_BATCH_KEYS if k in raw}
        item["id"] = str(raw.get("id") or nid)
        if "title" not in item:
            item["title"] = str(raw.get("title") or nid)
        compact[nid] = item
    return compact


def _format_emotion_arc(node: dict) -> str:
    if not isinstance(node, dict):
        return ""
    open_e = node.get("emotion_open") or ""
    trigger = node.get("emotion_trigger") or ""
    close_e = node.get("emotion_close") or ""
    action = node.get("emotion_action") or ""
    if not any((open_e, trigger, close_e, action)):
        return ""
    return (
        "【本场景情感弧】\n"
        f"  开场情绪：{open_e or '—'}\n"
        f"  触发事件：{trigger or '—'}\n"
        f"  收场情绪：{close_e or '—'}\n"
        f"  角色核心动作：{action or '—'}"
    )


def build_expand_system() -> str:
    return (
        "你是橙光视觉小说编剧，续写叙事对白场景。每句 24-80 汉字，忠于原文情节与 bible，"
        + "交代前因后果，勿缩成碎短句。保持 lines 多句点击续播格式。"
        + DIALOGUE_QUOTE_RULE
        + "只输出合法 JSON。"
    )


def build_expand_user(req_text: str, style: StylePreset, game: dict, node_id: str, choice_id: str) -> str:
    label = STYLE_LABELS[style]
    import json

    game_json = json.dumps(game, ensure_ascii=False, indent=2)
    return f"""玩家选择了分支，请续写 3-6 个新场景节点（橙光格式）。

原文参考：
{req_text}

风格：{label}
当前节点：{node_id}，选项：{choice_id}

【已有游戏】
{game_json}

输出 JSON：
{{
  "nodes": {{ "新id": {{ 同 StoryNode 结构，含 lines、image_prompt }} }},
  "updated_links": [{{"from_node":"","choice_id":"","next":""}}]
}}

新节点 lines：每场景 4-7 句，每句 24-80 汉字，保留关键剧情信息与情绪；含 1-2 个抉择点（各 2-4 个 choices）；至少 1 个结局节点。不要重复已有 id。
续写节点须含 chapter、chapter_title；若开启新章则填 chapter_blurb，否则留空。章节号应延续已有游戏最高章或同章。"""
