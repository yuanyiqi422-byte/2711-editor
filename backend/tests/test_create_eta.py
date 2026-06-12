from narrative_service import (
    build_create_eta,
    estimate_create_eta_label,
    estimate_outline_remaining_hint,
    estimate_scene_batch_hint,
)


def test_estimate_create_eta_label_scales_with_length():
    assert estimate_create_eta_label(1000) == "约 1–2 分钟"
    assert estimate_create_eta_label(3000) == "约 1–2 分钟"
    assert estimate_create_eta_label(6000) == "约 1–3 分钟"
    assert estimate_create_eta_label(12000) == "约 2–4 分钟"
    assert estimate_create_eta_label(20000) == "约 4–6 分钟"


def test_build_create_eta_includes_narrative_scale():
    eta = build_create_eta(20000)
    assert eta["label"] == "约 4–6 分钟"
    assert eta["tier"] == "短篇"
    assert eta["nodes_min"] >= 12
    assert eta["nodes_max"] <= 18
    assert eta["nodes_max"] >= eta["nodes_min"]
    assert eta["min_total_lines"] > 0


def test_estimate_outline_remaining_hint_long_text():
    assert "1–3" in estimate_outline_remaining_hint(20000)


def test_estimate_scene_batch_hint_long_text():
    assert estimate_scene_batch_hint(20000) == "长文本场景生成可能需 2–4 分钟"
    assert "1–3" in estimate_scene_batch_hint(8000)
