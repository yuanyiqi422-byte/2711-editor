"""轻量主角/角色名提取 — 用于捏脸确认页（启发式离线可用，可选 LLM 增强）。"""

from __future__ import annotations

import os
import re
from collections import Counter

# ── 非人名：指示词 / 代词 ──
_DEMONSTRATIVES = frozenset(
    """
    这儿 这里 那里 这边 那边 此处 彼处 此地 彼时 这时 那时 此时 当下 哪里 哪儿
    这 那 这个 那个 这些 那些 这样 那样 如此 这么 那么 怎的 为何 怎么 怎样
    """.split()
)

_PRONOUNS = frozenset(
    """
    我 你 您 他 她 它 咱 俺 吾 汝 尔 彼 此 谁 啥 什 嘛 呢 吧 啊 呀 哦 嗯
    我们 你们 他们 她们 它们 咱们 俺们 大家 各位 自己 本人 人家 别人 某人
    """.split()
)

# 单独出现时应排除的头衔/称谓（非专名）
_TITLES = frozenset(
    """
    师兄 师姐 师弟 师妹 师父 师傅 师尊 师叔 师伯 师祖 长老 掌门 宗主 教主
    殿下 陛下 皇上 圣上 王爷 公子 小姐 姑娘 少年 少女 青年 男子 女子 孩子
    老头 老者 大汉 壮汉 路人 旁人 对方 此人 那人 某人 阁下 足下 前辈
    晚辈 同门 道友 仙友 魔头 妖女 妖王 魔尊 剑仙 剑圣 剑神 道友 仙长
    """.split()
)

# 常见叙事/功能词、副词、量词、环境描写碎片
_STOP = frozenset(
    """
    他们 我们 你们 大家 这时 那时 此时 忽然 突然 只见 于是 但是 因为 所以
    如果 虽然 已经 还是 可以 不能 不是 什么 怎么 为什么 一个 一些 这位 那位
    今天 明天 昨天 上午 下午 晚上 清晨 深夜 学校 公司 城市 世界 中国 日本
    说道 问道 回答 心想 看着 听到 知道 觉得 开始 结束 第一 第二 第三 章节
    轻轻 慢慢 静静 默默 缓缓 渐渐 微微 淡淡 冷冷 竟然 居然 果然
    不过 然而 而且 并且 或者 以及 还有 正在 将要 可能 应该 必须 需要
    没有 并非 若是 便是 就是 只是 只有 只要 哪怕 即使 尽管 无论 不管
    风很 很大 很小 许多 不少 几个 一些 一点 一下 一声 一句 一眼 一番 一阵
    低声 轻声 沉声 冷声 怒声 回头 身后 身前 面前 眼前 耳边 心里 头上 脚下
    吹得 猎猎 作响 衣袂 云海 出神 崖边 走到 站 坐 躺 看 望 听 想 说 道
    不逼 逼你 知道 清楚 自己 清楚 明白 为何 怎样 如何 到底 究竟 难道
    """.split()
)

# 常见中文姓（用于加分，非必须）
_SURNAMES = frozenset(
    "李王张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文"
)  # char-level singles

_COMPOUND_SURNAMES = frozenset({"欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "令狐", "慕容", "宇文", "长孙"})

# ── 高置信度命名模式 ──
_INTRO_NAME = re.compile(
    r"(?:叫|名为|名叫|乃是|称作|唤作|改名|唤名)[「『""]?([\u4e00-\u9fff]{2,4})"
)
_POV_NAME = re.compile(
    r"(?:我是|我叫|吾乃|本座乃|某乃)([\u4e00-\u9fff]{2,4})"
)
_ROLE_HINT = re.compile(
    r"(?:主角|男主|女主|主人公|叙述者)(?:叫|名为|是|名叫)?[「『""]?([\u4e00-\u9fff]{2,4})"
)
_SPEAKER_LABEL = re.compile(r"(?:^|\n)\s*([\u4e00-\u9fff]{2,4})\s*[：:]")
_SPEAKER_VERB = re.compile(
    r"([\u4e00-\u9fff]{2,4})(?:低声|轻声|沉声|冷声|怒声|缓缓|慢慢|轻轻)?(?:说|道|问|答|笑|喊|叫)[：:，,]"
)
_NARRATIVE_NAME = re.compile(
    r"([\u4e00-\u9fff]{2,3})(?:的|地|与|和|同|向|往|是|有|无|被|让|给|从|到|于|为|在|见|遇|带|领|随|伴|等|找|寻|请|访|称|号|名|站|走|跑|坐|躺|看|望|听|想|回|转|来|去|出|入|开|关|笑|哭|叹|道)"
)
# 译名 / 经典文学人名（无常见姓亦可）
_STATION_NAME = re.compile(r"([\u4e00-\u9fff]{3,4})(?:在(?:车|火)站|在站台)")
_MEET_NAME = re.compile(r"(?:遇见|碰见|见到|遇到)(?:了)?([\u4e00-\u9fff]{2,4})")
_DOTTED_NAME = re.compile(r"([\u4e00-\u9fff]{2,4})·[\u4e00-\u9fff]")
_QUOTE = re.compile(
    r"[\u300c\u300e\u201c\u2018「『][^\u300d\u300f\u201d\u2019」』]*[\u300d\u300f\u201d\u2019」』]"
)

_VERB_PHRASE = re.compile(
    r"^(?:不|没|别|莫|勿|未|非|岂|怎|何|难|休|毋|无)[\u4e00-\u9fff]{0,2}[你我他她它]?$|"
    r"^[你我他她它][的地得]?$|"
    r".*[了着过]$|"
    r"^[能否会要该当须].*|"
    r".*(?:一下|一点|一声|一句|一眼|一番|一阵|一些|许多|怎么|为何|什么|哪里|哪儿|清楚|明白)$"
)

_BAD_INNER = frozenset("的了在是有和与或把被让给从到不在没别非莫勿未岂怎何吗呢吧啊呀哦嗯个下以")
_BAD_PREFIX_CHARS = frozenset("对向往从跟和与给把将被让在到为以于按望着吹衣猎兄师这那他她它你我")
_BAD_NAME_SUFFIX = frozenset("站走跑看听说想觉感应心脸面手头眼边处回前后上下来去道声风大响")

MIN_CONFIDENCE_SCORE = 18
HIGH_CONFIDENCE_SCORE = 45
MEDIUM_CONFIDENCE_SCORE = 28


def _has_ai_key() -> bool:
    key = os.getenv("AI_API_KEY", "").strip()
    return bool(key) and key != "your-secret-key-here"


def _score_to_confidence(score: int) -> int:
    """将内部分数映射为 0–100 展示置信度。"""
    if score >= HIGH_CONFIDENCE_SCORE:
        return min(100, 55 + score // 2)
    if score >= MEDIUM_CONFIDENCE_SCORE:
        return min(74, 35 + score)
    if score >= MIN_CONFIDENCE_SCORE:
        return min(54, 20 + score // 2)
    return max(0, score)


def _is_title_only(name: str) -> bool:
    if name in _TITLES:
        return True
    for title in _TITLES:
        if len(title) < 2:
            continue
        if name == title:
            return True
        if name.startswith(title) and len(name) <= len(title) + 1:
            return True
        if name.endswith(title) and len(name) > len(title):
            prefix = name[: -len(title)]
            if 1 <= len(prefix) <= 2 and prefix[0] in _SURNAMES:
                continue
            return True
        if len(name) <= 4 and title in name and name not in _SURNAMES:
            return True
    return False


def _has_surname(name: str) -> bool:
    if name and name[0] in _SURNAMES:
        return True
    return len(name) >= 2 and name[:2] in _COMPOUND_SURNAMES


_MAX_FRAGMENT_PAD = 3


_KNOWN_BAD_NAME_SLICES = frozenset({"尔斯泰", "伦斯基", "他下个礼"})


def _is_suffix_of_longer_cjk_token(name: str, text: str) -> bool:
    """Reject name if any CJK token in text strictly contains it (e.g. 托尔斯泰→尔斯泰)."""
    if not name or not text or _has_surname(name):
        return False
    for m in re.finditer(r"[\u4e00-\u9fff]{2,}", text):
        word = m.group(0)
        if len(word) <= len(name):
            continue
        if word.endswith(name):
            return True
        if word.startswith(name) and name[0] in "他她它你我这那":
            return True
    return False


def _is_bad_token_slice(name: str, text: str) -> bool:
    """检测错误分词切片：如「他下个礼」←「他下个礼拜」、「尔斯泰」←「托尔斯泰」。"""
    if not name or not text:
        return False
    for m in re.finditer(re.escape(name), text):
        start, end = m.start(), m.end()

        left = start
        for _ in range(_MAX_FRAGMENT_PAD):
            if left > 0 and "\u4e00" <= text[left - 1] <= "\u9fff":
                left -= 1
            else:
                break
        prefix = text[left:start]
        if (
            prefix
            and len(prefix) <= _MAX_FRAGMENT_PAD
            and text[left:end].endswith(name)
            and not _has_surname(name)
        ):
            return True

        right = end
        for _ in range(_MAX_FRAGMENT_PAD):
            if right < len(text) and "\u4e00" <= text[right] <= "\u9fff":
                right += 1
            else:
                break
        suffix = text[end:right]
        if suffix and len(suffix) <= _MAX_FRAGMENT_PAD:
            if text[start:right].startswith(name) and name[0] in "他她它你我这那":
                return True
            if (
                prefix
                and not _has_surname(name)
                and not text[left:end].endswith(name)
                and not text[start:right].startswith(name)
            ):
                return True
    return False


def _is_embedded_in_longer_name(name: str, text: str) -> bool:
    """无姓氏名是否为更长 CJK 词内的尾/前缀碎片（LLM 误拆专用）。"""
    if not name or not text:
        return False
    if name in _KNOWN_BAD_NAME_SLICES:
        return True
    if _has_surname(name):
        return False
    if _is_bad_token_slice(name, text):
        return True
    return _is_suffix_of_longer_cjk_token(name, text)


def _has_particle_or_punct(name: str) -> bool:
    if re.search(r"[^\u4e00-\u9fff]", name):
        return True
    for ch in name:
        if ch in _BAD_INNER:
            return True
    return False


def _is_likely_fragment(name: str, *, text: str = "") -> bool:
    """排除对话/描写中的短语碎片。"""
    if name in _STOP or name in _DEMONSTRATIVES:
        return True
    # 2 字无姓氏且不在高置信模式 — 很可能是动词短语
    if len(name) == 2 and not _has_surname(name):
        if name[0] in "对向从跟和与给把被让在到为以于" or name[1] in "的了着过":
            return True
        if name in {"回头", "身后", "面前", "低声", "轻轻", "慢慢", "知道", "清楚", "明白", "如何", "为何"}:
            return True
    # 3 字无姓氏且末字为动词/副词
    if len(name) == 3 and not _has_surname(name):
        if name[-1] in "了着过" or name[-1] in _BAD_NAME_SUFFIX:
            return True
        if name.startswith(("不", "没", "别", "莫", "勿", "未", "非")):
            return True
    if text and _is_embedded_in_longer_name(name, text):
        return True
    return False


def _is_plausible_name(name: str, *, strict: bool = False, text: str = "") -> bool:
    if not name or len(name) < 2 or len(name) > 4:
        return False
    if name in _STOP or name in _DEMONSTRATIVES or name in _PRONOUNS:
        return False
    if _is_title_only(name):
        return False
    if _VERB_PHRASE.search(name):
        return False
    if _has_particle_or_punct(name):
        return False
    if _is_likely_fragment(name, text=text):
        return False
    if any(ch in name for ch in _BAD_INNER):
        return False
    if name[0] in _BAD_PREFIX_CHARS:
        return False
    if name[-1] in _BAD_NAME_SUFFIX:
        return False
    for p in _PRONOUNS:
        if len(p) >= 2 and p in name:
            return False
    if all(ch in "这那你我他她它" for ch in name):
        return False
    if strict and len(name) == 2 and not _has_surname(name):
        return False
    return True


def _narrative_text(sample: str) -> str:
    """去掉引号内对话，保留叙述段落用于计分。"""
    return _QUOTE.sub(" ", sample)


def _surname_bonus(name: str) -> int:
    if name and name[0] in _SURNAMES:
        return 5
    if len(name) >= 2 and name[:2] in _COMPOUND_SURNAMES:
        return 7
    return 0


def _dedupe_substring_names(candidates: list[dict]) -> list[dict]:
    """若已有更长专名包含短名，丢弃短名。"""
    names = [c["name"] for c in candidates]
    keep: list[dict] = []
    for c in candidates:
        n = c["name"]
        if any(n != other and n in other and len(other) > len(n) for other in names):
            continue
        keep.append(c)
    return keep


def _score_candidates(sample: str) -> Counter[str]:
    scores: Counter[str] = Counter()
    narrative = _narrative_text(sample)
    early = sample[:2500]

    def add(name: str, pts: int, *, only_narrative: bool = False, strict: bool = False) -> None:
        n = name.strip()
        if not _is_plausible_name(n, strict=strict, text=sample):
            return
        if only_narrative and n not in narrative:
            return
        scores[n] += pts + _surname_bonus(n)

    for m in _INTRO_NAME.finditer(sample):
        add(m.group(1), 65)
    for m in _POV_NAME.finditer(sample):
        add(m.group(1), 60)
    for m in _ROLE_HINT.finditer(sample):
        add(m.group(1), 55)

    for m in _STATION_NAME.finditer(sample):
        add(m.group(1), 42, strict=False)
    for m in _MEET_NAME.finditer(sample):
        add(m.group(1), 38, strict=False)
    for m in _DOTTED_NAME.finditer(sample):
        add(m.group(1), 36, strict=False)

    for m in _SPEAKER_LABEL.finditer(sample):
        n = m.group(1).strip()
        if _has_surname(n):
            add(n, 28)
        elif _is_plausible_name(n, text=sample):
            add(n, 12, strict=True)

    for m in _SPEAKER_VERB.finditer(sample):
        n = m.group(1).strip()
        if _has_surname(n):
            add(n, 20)
        elif _is_plausible_name(n, strict=True, text=sample):
            add(n, 10)

    for m in _NARRATIVE_NAME.finditer(narrative):
        add(m.group(1), 7, only_narrative=True, strict=True)

    tokens = [
        m.group(0)
        for m in re.finditer(r"[\u4e00-\u9fff]{2,3}", narrative)
        if _is_plausible_name(m.group(0), strict=True, text=sample)
    ]
    for name, count in Counter(tokens).items():
        if count >= 2:
            add(name, min(count * 4, 14))

    for m in _NARRATIVE_NAME.finditer(_narrative_text(early)):
        n = m.group(1).strip()
        if _is_plausible_name(n, strict=True, text=sample):
            scores[n] += 10

    freq = Counter(
        m.group(1)
        for m in _NARRATIVE_NAME.finditer(narrative)
        if _is_plausible_name(m.group(1), strict=True, text=sample)
    )
    for name, count in freq.items():
        if count >= 2:
            scores[name] += min(count * 2, 10)

    return scores


def _format_candidates(scores: Counter[str], limit: int) -> list[dict]:
    ranked = scores.most_common(limit * 4)
    out: list[dict] = []
    seen: set[str] = set()

    for name, score in ranked:
        if name in seen or score < MIN_CONFIDENCE_SCORE:
            continue
        seen.add(name)
        role = "主角" if not out else "主要角色"
        conf = _score_to_confidence(score)
        out.append({"name": name, "role": role, "score": score, "confidence": conf})
        if len(out) >= limit:
            break

    return _dedupe_substring_names(out)[:limit]


def extract_protagonist_candidates(text: str, limit: int = 3) -> list[dict]:
    """从小说文本启发式提取 1–3 个可能主角名（离线可用）。"""
    if not text or len(text.strip()) < 20:
        return []

    sample = text.strip()[:12000]
    scores = _score_candidates(sample)
    return _format_candidates(scores, limit)


async def extract_protagonist_candidates_llm(text: str, limit: int = 3) -> list[dict]:
    """可选 LLM 增强：单次快速调用（超时回退启发式）。"""
    if not _has_ai_key():
        return []

    import asyncio

    from llm import LLMError, chat_json

    sample = text.strip()[:5000]
    system = (
        "你是中文小说角色分析助手。从片段中识别真实人名（2-4个汉字）。"
        "排除：指示词（这儿/这里/那里）、代词、头衔（师兄/师父/长老）、"
        "动词短语（不逼你/风很/轻轻/低声）、环境描写词、从更长词切出的碎片（如他下个礼/尔斯泰）。"
        "只返回完整专名（2-4个汉字），优先中文姓名；音译人名须完整（如托尔斯泰、渥伦斯基）。"
        "只返回 JSON，无把握则 characters 为空。"
    )
    user = (
        f"片段：\n{sample}\n\n"
        f'返回 {{"characters":[{{"name":"人名","role":"主角|主要角色","score":0-100}}]}}，'
        f"最多 {limit} 个，按主角可能性排序。"
    )
    try:
        data = await asyncio.wait_for(
            chat_json(
                system,
                user,
                temperature=0.15,
                max_tokens=200,
                max_attempts=1,
                fast_model=True,
            ),
            timeout=12.0,
        )
    except (LLMError, asyncio.TimeoutError, TimeoutError):
        return []

    raw = data.get("characters") or []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if (
            not _is_plausible_name(name, text=sample)
            or name in seen
            or _is_embedded_in_longer_name(name, sample)
        ):
            continue
        seen.add(name)
        llm_score = int(item.get("score") or 50)
        if not _has_surname(name) and (llm_score < 80 or len(name) < 3):
            continue
        role = str(item.get("role") or ("主角" if not out else "主要角色"))
        out.append({
            "name": name,
            "role": role,
            "score": max(llm_score, 40),
            "confidence": min(100, llm_score),
        })
        if len(out) >= limit:
            break
    return out


def _merge_candidates(primary: list[dict], secondary: list[dict], limit: int) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for src in (primary, secondary):
        for c in src:
            n = c["name"]
            if n in seen:
                continue
            seen.add(n)
            merged.append(c)
            if len(merged) >= limit:
                return _dedupe_substring_names(merged)
    return _dedupe_substring_names(merged)


async def extract_protagonist_candidates_enhanced(text: str, limit: int = 3) -> dict:
    """
    启发式即时可用；有 API Key 时并行尝试 LLM（12s 超时），取更可信结果。
    返回 {characters, low_confidence}。
    """
    import asyncio

    heuristic = extract_protagonist_candidates(text, limit=limit)
    heur_top = heuristic[0]["confidence"] if heuristic else 0

    if not _has_ai_key():
        return {
            "characters": heuristic,
            "low_confidence": not heuristic or heur_top < 55,
        }

    llm_task = asyncio.create_task(extract_protagonist_candidates_llm(text, limit=limit))

    # 启发式置信度足够时不必等 LLM（避免 preview 端点被慢模型拖住）
    if heur_top >= 70 and heuristic:
        llm_task.cancel()
        return {"characters": heuristic, "low_confidence": heur_top < 55}

    try:
        llm_chars = await asyncio.wait_for(llm_task, timeout=14.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        llm_chars = []
    if llm_chars:
        sample_full = text.strip()[:12000]
        validated = [
            c
            for c in llm_chars
            if _is_plausible_name(c["name"], text=sample_full)
            and not _is_embedded_in_longer_name(c["name"], sample_full)
        ]
        if validated and validated[0]["confidence"] >= 55:
            merged = _merge_candidates(validated, heuristic, limit)
            top_conf = merged[0]["confidence"] if merged else 0
            return {
                "characters": merged,
                "low_confidence": top_conf < 55,
            }

    return {
        "characters": heuristic,
        "low_confidence": not heuristic or heur_top < 55,
    }


# ── 诊断样本（python -m character_extract 或 scripts/_diag_protagonist.py）──
_DIAG_SAMPLES: dict[str, str] = {
    "false_positive_trap": """
林婉儿站在崖边，望着云海出神。这儿风很大，吹得她衣袂猎猎作响。
师兄轻轻走到她身后，低声道：「不逼你了，你自己想清楚。」
林婉儿回头，对师兄说：「我知道。」
这里不是名字，那里也不是。他她它我们你们都不该出现。
""",
    "intro_pattern": """
第一章 初入宗门
主角名叫苏清歌，乃是青云宗外门弟子。
苏清歌的剑法尚浅，却在晨雾中独自练剑。
""",
    "pov_pattern": """
我叫陈默，在这个世界已经待了三年。
陈默走在雨巷里，心想这一切何时才能结束。
""",
    "garbage_only": "这儿风很大。那里没有人。师兄师姐师父都在。不逼你了。怎么这样。",
}


if __name__ == "__main__":
    import json

    for label, sample in _DIAG_SAMPLES.items():
        print(f"\n=== {label} ===")
        result = extract_protagonist_candidates(sample)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        bad = {"这儿", "这里", "那里", "师兄", "不逼你", "风很", "轻轻", "低声"}
        found = bad.intersection({c["name"] for c in result})
        if found:
            print(f"FAIL false positives: {found}")
        elif label == "garbage_only" and result:
            print("FAIL expected empty for garbage")
        elif label in ("false_positive_trap", "intro_pattern", "pov_pattern") and (
            not result or result[0]["name"] not in ("林婉儿", "苏清歌", "陈默")
        ):
            print(f"FAIL unexpected top: {result}")
