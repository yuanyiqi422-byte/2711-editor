"""场景图谱结构校验（代码层，非 LLM 自觉）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from models import choice_text_set_signature, normalize_choice_text_key, MAX_CHOICE_TEXT_USES


def count_ending_nodes(nodes: Mapping[str, dict]) -> int:
    """统计 is_ending=true 的节点数。"""
    return sum(
        1
        for raw in nodes.values()
        if isinstance(raw, dict) and bool(raw.get("is_ending"))
    )


def validate_choice_text_diversity(
    nodes: Mapping[str, dict],
    *,
    max_duplicate_ratio: float = 0.5,
) -> list[str]:
    """Reject graphs where too many choice nodes share identical option text sets."""
    signatures: list[tuple[str, ...]] = []
    for raw in nodes.values():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if not isinstance(choices, list) or len(choices) < 2:
            continue
        sig = choice_text_set_signature(choices)
        if len(sig) >= 2:
            signatures.append(sig)
    if len(signatures) < 2:
        return []
    counts = Counter(signatures)
    most_common_sig, dup_count = counts.most_common(1)[0]
    ratio = dup_count / len(signatures)
    if ratio > max_duplicate_ratio:
        return [
            "超过 50% 抉择节点选项文案相同"
            f"（{dup_count}/{len(signatures)} 组重复，示例：{list(most_common_sig)[:2]}）"
        ]
    return []


def validate_choice_text_frequency(
    nodes: Mapping[str, dict],
    *,
    max_uses: int = MAX_CHOICE_TEXT_USES,
) -> list[str]:
    """Fail when any normalized choice text appears more than max_uses times game-wide."""
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for raw in nodes.values():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if not isinstance(choices, list):
            continue
        for ch in choices:
            if not isinstance(ch, dict):
                continue
            text = str(ch.get("text") or "").strip()
            key = normalize_choice_text_key(text)
            if not key:
                continue
            counts[key] += 1
            display.setdefault(key, text)
    errors: list[str] = []
    for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if count > max_uses:
            sample = display.get(key, key)
            errors.append(
                f"选项文案「{sample}」全剧出现 {count} 次，超过上限 {max_uses} 次"
            )
    return errors


def count_choice_nodes(nodes: Mapping[str, dict]) -> int:
    """统计含 ≥2 个有效选项的非结局节点数。"""
    count = 0
    for raw in nodes.values():
        if not isinstance(raw, dict) or raw.get("is_ending"):
            continue
        choices = raw.get("choices") or []
        if isinstance(choices, list) and len(choices) >= 2:
            count += 1
    return count


def _choice_impact_level(ch: dict) -> str:
    imp = str(ch.get("impact") or "").strip().lower()
    if imp in ("low", "medium", "high"):
        return imp
    weight = ch.get("weight")
    try:
        w = int(weight) if weight is not None and weight != "" else 0
    except (TypeError, ValueError):
        w = 0
    if w >= 3:
        return "high"
    if w == 1:
        return "low"
    if w == 2:
        return "medium"
    hint = str(ch.get("narrative_impact") or "").lower()
    if any(k in hint for k in ("结局", "ending", "分支", "路线", "命运")):
        return "high"
    if any(k in hint for k in ("好感", "关系", "氛围", "语气", "微调")):
        return "low"
    return "medium"


def _max_linear_chain(nodes: Mapping[str, dict], start_node_id: str) -> int:
    """从起点沿 after_lines_next 的最长连续自动过渡链。"""
    if start_node_id not in nodes:
        return 0
    best = 0
    seen_paths: set[str] = set()

    def _walk(nid: str, depth: int) -> None:
        nonlocal best
        if nid in seen_paths or nid not in nodes:
            best = max(best, depth)
            return
        seen_paths.add(nid)
        raw = nodes[nid]
        if raw.get("is_ending"):
            best = max(best, depth)
            seen_paths.discard(nid)
            return
        choices = raw.get("choices") or []
        if isinstance(choices, list) and len(choices) >= 2:
            best = max(best, depth)
            seen_paths.discard(nid)
            return
        nxt = str(raw.get("after_lines_next") or "").strip()
        if nxt and nxt in nodes:
            _walk(nxt, depth + 1)
        else:
            best = max(best, depth)
        seen_paths.discard(nid)

    _walk(start_node_id, 0)
    return best


def validate_outline_structure(
    nodes: Mapping[str, dict],
    start_node_id: str,
    *,
    min_endings: int = 3,
    min_choice_nodes: int = 0,
    choice_ratio_min: float = 0.35,
    choice_ratio_max: float = 0.65,
    min_high_impact_branches: int = 2,
    max_linear_chain: int = 5,
    relaxed: bool = False,
) -> list[str]:
    """校验骨架 dict；返回错误列表，空列表表示通过。"""
    if relaxed:
        choice_ratio_min = min(choice_ratio_min, 0.22)
        choice_ratio_max = max(choice_ratio_max, 0.78)
        min_high_impact_branches = min(min_high_impact_branches, 1)
        max_linear_chain = max(max_linear_chain, 8)
    errors: list[str] = []
    if not nodes:
        return ["nodes 为空"]
    if start_node_id not in nodes:
        errors.append(f"start_node_id「{start_node_id}」不存在")

    ending_types: set[str] = set()
    choice_nodes = 0
    non_ending = 0
    high_impact_choices = 0

    for nid, raw in nodes.items():
        if not isinstance(raw, dict):
            errors.append(f"节点「{nid}」不是对象")
            continue
        is_ending = bool(raw.get("is_ending"))
        choices = raw.get("choices") or []
        after_next = str(raw.get("after_lines_next") or "").strip()

        if is_ending:
            et = str(raw.get("ending_type") or "").strip()
            if et:
                ending_types.add(et)
            if choices:
                errors.append(f"结局节点「{nid}」不应含 choices")
            if after_next:
                errors.append(f"结局节点「{nid}」不应含 after_lines_next")
            continue

        non_ending += 1
        choice_count = len(choices) if isinstance(choices, list) else 0
        if isinstance(choices, list) and 0 < choice_count < 2:
            errors.append(f"节点「{nid}」分支节点至少需要 2 个 choices")
        has_choices = choice_count >= 2
        has_auto = bool(after_next and after_next in nodes)

        if choice_count == 1:
            errors.append(f"节点「{nid}」仅 1 个选项，须 2-4 个")
        elif choice_count > 4:
            errors.append(f"节点「{nid}」选项过多（{choice_count}），最多 4 个")

        if not has_choices and not has_auto:
            errors.append(f"节点「{nid}」缺少有效 choices 或 after_lines_next")

        if has_choices:
            choice_nodes += 1
            sigs: list[tuple[str, str, str]] = []
            for ch in choices:
                if not isinstance(ch, dict):
                    continue
                nxt = str(ch.get("next") or "")
                if nxt and nxt not in nodes:
                    errors.append(f"节点「{nid}」选项指向未知 id「{nxt}」")
                imp = str(ch.get("impact") or "").strip().lower()
                if imp not in ("low", "medium", "high"):
                    cid = str(ch.get("id") or "?")
                    errors.append(
                        f"节点「{nid}」选项「{cid}」须标注 impact（low/medium/high）"
                    )
                imm = str(ch.get("immediate_consequence") or ch.get("consequence_hint") or "").strip()
                impact = str(ch.get("narrative_impact") or ch.get("impact") or "").strip()
                if not impact:
                    errors.append(f"节点「{nid}」选项缺少 narrative_impact/impact")
                sigs.append((imm, impact, nxt))
                if _choice_impact_level(ch) == "high":
                    high_impact_choices += 1
            if len(sigs) >= 2 and len(set(sigs)) < len(sigs):
                errors.append(f"节点「{nid}」存在 immediate_consequence/narrative_impact 相同的伪分支")

        elif after_next and after_next not in nodes:
            errors.append(f"节点「{nid}」after_lines_next 无效：{after_next}")

    total = len(nodes)
    if non_ending >= 4:
        ratio = choice_nodes / non_ending
        if ratio < choice_ratio_min or ratio > choice_ratio_max:
            errors.append(
                f"抉择点占比 {ratio:.0%} 不在 {choice_ratio_min:.0%}–{choice_ratio_max:.0%} 区间"
                f"（{choice_nodes}/{non_ending} 个非结局节点含选项）"
            )

    if total >= 8:
        if min_choice_nodes > 0 and choice_nodes < min_choice_nodes:
            errors.append(
                f"抉择点仅 {choice_nodes} 个，至少需要 {min_choice_nodes} 个（须来自原文冲突/抉择）"
            )
        if high_impact_choices < min_high_impact_branches:
            errors.append(
                f"高影响选项仅 {high_impact_choices} 个，至少需要 {min_high_impact_branches} 个"
                "（impact=high，导向不同路线/结局）"
            )

    if start_node_id in nodes:
        linear_chain = _max_linear_chain(nodes, start_node_id)
        if linear_chain > max_linear_chain:
            errors.append(
                f"线性过渡链过长（{linear_chain} 连跳），须在原文节拍处插入 2-4 选项的抉择点"
            )

        reachable = _reachable_from(nodes, start_node_id)
        unreachable = set(nodes.keys()) - reachable
        if unreachable:
            errors.append(f"不可达节点 {len(unreachable)} 个（如 {next(iter(unreachable))}）")

        dead_ends = _dead_end_nodes(nodes, reachable)
        if dead_ends:
            sample = ", ".join(list(dead_ends)[:3])
            errors.append(f"非结局死路节点：{sample}")

        good_ok = _has_reachable_ending(nodes, reachable, {"good"})
        bad_ok = _has_reachable_ending(
            nodes, reachable, {"bad", "neutral", "open", "hidden"}
        )
        if not good_ok:
            errors.append("从起点不可达任何 good 结局")
        if not bad_ok:
            errors.append("从起点不可达任何 bad/neutral 类结局")

    ending_count = count_ending_nodes(nodes)
    if min_endings > 0 and ending_count < min_endings:
        errors.append(f"结局节点仅 {ending_count} 个，至少需要 {min_endings} 个互不相同的结局")

    if ending_types and "good" not in ending_types:
        errors.append("结局类型缺少 good")
    if ending_types and not ending_types.intersection({"bad", "neutral"}):
        errors.append("结局类型缺少 bad 或 neutral")

    errors.extend(validate_choice_text_diversity(nodes))
    errors.extend(validate_choice_text_frequency(nodes))

    return errors


_OUTLINE_CRITICAL_KEYWORDS = (
    "为空",
    "不存在",
    "不可达",
    "死路",
    "不可达任何",
    "缺少 good",
    "缺少 bad",
)

_OUTLINE_SOFT_KEYWORDS = (
    "抉择点占比",
    "高影响选项",
    "线性过渡链",
    "伪分支",
    "impact（low/medium/high）",
    "narrative_impact",
    "全剧出现",
)


def outline_soft_pass(errors: list[str], node_count: int) -> bool:
    """首轮大纲若仅少量非致命校验失败（≈65% 通过），直接采纳避免重试。"""
    if not errors:
        return True
    hard = [
        e
        for e in errors
        if any(k in e for k in _OUTLINE_CRITICAL_KEYWORDS)
        and not any(k in e for k in ("抉择点仅", "结局节点仅"))
    ]
    if hard:
        return False
    soft_only = all(any(k in e for k in _OUTLINE_SOFT_KEYWORDS) for e in errors)
    budget = max(6, node_count + 6)
    threshold = max(2, int(budget * 0.35))
    if soft_only:
        threshold = max(threshold, len(errors))
    return len(errors) <= threshold


def _reachable_from(nodes: Mapping[str, dict], start: str) -> set[str]:
    seen: set[str] = set()
    queue = [start]
    while queue:
        nid = queue.pop(0)
        if nid in seen or nid not in nodes:
            continue
        seen.add(nid)
        raw = nodes[nid]
        if raw.get("is_ending"):
            continue
        nxt = str(raw.get("after_lines_next") or "").strip()
        if nxt and nxt in nodes:
            queue.append(nxt)
        for ch in raw.get("choices") or []:
            if isinstance(ch, dict):
                cn = str(ch.get("next") or "")
                if cn in nodes:
                    queue.append(cn)
    return seen


def _dead_end_nodes(nodes: Mapping[str, dict], reachable: set[str]) -> set[str]:
    dead: set[str] = set()
    for nid in reachable:
        raw = nodes[nid]
        if raw.get("is_ending"):
            continue
        nxt = str(raw.get("after_lines_next") or "").strip()
        choices = raw.get("choices") or []
        has_valid_auto = bool(nxt and nxt in nodes)
        has_valid_choice = any(
            isinstance(c, dict) and str(c.get("next") or "") in nodes for c in choices
        )
        if not has_valid_auto and not has_valid_choice:
            dead.add(nid)
    return dead


def _has_reachable_ending(
    nodes: Mapping[str, dict],
    reachable: set[str],
    types: set[str],
) -> bool:
    for nid in reachable:
        raw = nodes[nid]
        if not raw.get("is_ending"):
            continue
        et = str(raw.get("ending_type") or "").strip()
        if et in types:
            return True
    return False
