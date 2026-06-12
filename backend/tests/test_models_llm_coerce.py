"""LLM JSON null 字段应被模型层归一化，避免 Pydantic 校验失败。"""

from models import ChoiceOption, DialogueLine, StoryNode


def test_story_node_after_lines_next_null_becomes_empty():
    node = StoryNode.model_validate(
        {
            "id": "scene_1",
            "title": "开场",
            "after_lines_next": None,
            "choices": None,
            "lines": None,
            "is_ending": None,
            "chapter": None,
        }
    )
    assert node.after_lines_next == ""
    assert node.choices == []
    assert node.lines == []
    assert node.is_ending is False
    assert node.chapter == 1


def test_choice_option_null_hint_becomes_empty():
    opt = ChoiceOption.model_validate(
        {"id": "a", "text": "选 A", "next": "scene_2", "consequence_hint": None}
    )
    assert opt.consequence_hint == ""


def test_choice_option_impact_and_weight_coerce():
    opt = ChoiceOption.model_validate(
        {
            "id": "a",
            "text": "选 A",
            "next": "scene_2",
            "impact": "high",
            "weight": 3,
        }
    )
    assert opt.impact == "high"
    assert opt.resolved_impact() == "high"
    low = ChoiceOption.model_validate(
        {"id": "b", "text": "选 B", "next": "scene_3", "weight": 1}
    )
    assert low.resolved_impact() == "low"


def test_dialogue_line_null_speaker_becomes_empty():
    line = DialogueLine.model_validate({"speaker": None, "text": "你好", "portrait": None})
    assert line.speaker == ""
    assert line.portrait == ""
