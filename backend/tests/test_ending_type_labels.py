"""结局类型须归一为英文枚举，UI 标签为文学收束语（非好/坏/普通结局）。"""

from models import (
    StoryNode,
    canonical_ending_type,
    derive_literary_ending_title,
    ending_type_label,
    is_broken_ending_title,
    normalize_ending_node_fields,
    sanitize_ending_node_title,
)


def test_canonical_ending_type_maps_aliases():
    assert canonical_ending_type("neutral") == "neutral"
    assert canonical_ending_type("Neutral 结局") == "neutral"
    assert canonical_ending_type("平和结局") == "neutral"
    assert canonical_ending_type("好结局") == "good"
    assert canonical_ending_type("BE") == "bad"


def test_ending_type_label_is_literary_not_moral():
    assert ending_type_label("neutral") == "晚风里的秘密"
    assert ending_type_label("good") == "青春就此落款"
    assert ending_type_label("bad") == "风过徒留怅惘"
    assert ending_type_label("true") == "真相终于揭晓"
    assert ending_type_label("hidden") == "幽径独行无人知"
    assert "好结局" not in ending_type_label("good")
    assert "neutral" not in ending_type_label("neutral")


def test_is_broken_ending_title_detects_beat_snippet_garbage():
    assert is_broken_ending_title("夏备战高已远，平淡收场")
    assert is_broken_ending_title("备战高已远，平淡收场")
    assert is_broken_ending_title("高潮成空，徒留怅惘")
    assert is_broken_ending_title("好结局")
    assert is_broken_ending_title("neutral 结局")
    assert not is_broken_ending_title("晚风里的秘密")
    assert not is_broken_ending_title("青春就此落款")
    assert not is_broken_ending_title("雨夜重逢")


def test_derive_literary_ending_title_prefers_node_title():
    title = derive_literary_ending_title("neutral", title="雨夜重逢")
    assert title == "雨夜重逢"


def test_derive_literary_ending_title_from_beat_not_moral():
    title = derive_literary_ending_title("good", beat="主角在雨夜做出最后抉择")
    assert "好结局" not in title
    assert "good" not in title.lower()
    assert len(title) >= 4
    assert not is_broken_ending_title(title)
    assert "已远" not in title
    assert "成空" not in title


def test_derive_literary_ending_title_never_uses_beat_snippet():
    """Campus/高考 beat must not produce truncated snippet titles."""
    title = derive_literary_ending_title(
        "neutral",
        beat="高三夏备战高考收束，各奔前程",
        mood="neutral",
    )
    assert title != "夏备战高已远，平淡收场"
    assert not is_broken_ending_title(title)
    assert "备战" not in title or title in (
        "晚风里的秘密",
        "云卷云舒各安",
        "潮起潮落至此",
        "生活回到寻常",
        "平淡收场也罢",
        "各安其所如是",
    )


def test_derive_literary_ending_title_rejects_moral_title():
    title = derive_literary_ending_title("bad", title="坏结局", beat="高潮")
    assert title != "坏结局"
    assert "坏结局" not in title


def test_derive_literary_ending_title_rejects_broken_node_title():
    title = derive_literary_ending_title(
        "neutral",
        title="夏备战高已远，平淡收场",
        beat="备战高考",
    )
    assert title != "夏备战高已远，平淡收场"
    assert not is_broken_ending_title(title)


def test_sanitize_ending_node_title_strips_english_leakage():
    assert sanitize_ending_node_title("neutral 结局", "neutral") == ""
    assert sanitize_ending_node_title("good结局", "good") == ""
    assert sanitize_ending_node_title("雨夜重逢", "neutral") == "雨夜重逢"
    assert sanitize_ending_node_title("好结局", "good") == ""


def test_normalize_ending_node_fields_rewrites_bad_title():
    et, title = normalize_ending_node_fields(
        is_ending=True,
        ending_type="neutral",
        title="neutral 结局",
    )
    assert et == "neutral"
    assert title == "晚风里的秘密"
    assert "neutral" not in title.lower()
    assert "普通结局" not in title


def test_normalize_ending_node_fields_rewrites_broken_snippet_title():
    et, title = normalize_ending_node_fields(
        is_ending=True,
        ending_type="neutral",
        title="夏备战高已远，平淡收场",
    )
    assert et == "neutral"
    assert not is_broken_ending_title(title)
    assert title != "夏备战高已远，平淡收场"


def test_skeleton_ending_titles_are_literary_not_moral():
    from narrative_service import _skeleton_from_bible

    skeleton, _ = _skeleton_from_bible(
        {"plot_beats": ["开端", "冲突", "高三备战高考", "收束"]},
        5000,
    )
    for eid in ("ending_good", "ending_bad", "ending_neutral"):
        assert eid in skeleton
        title = skeleton[eid]["title"]
        assert "好结局" not in title
        assert "坏结局" not in title
        assert "普通结局" not in title
        assert len(title) >= 4
        assert not is_broken_ending_title(title)
        assert "已远，平淡收场" not in title


def test_story_node_validator_canonicalizes_ending_type():
    node = StoryNode.model_validate(
        {
            "id": "end_neutral",
            "title": "neutral 结局",
            "is_ending": True,
            "ending_type": "Neutral 结局",
            "lines": [{"speaker": "旁白", "text": "没有吃过人的孩子终于回到了人间。"}],
        }
    )
    assert node.ending_type == "neutral"
