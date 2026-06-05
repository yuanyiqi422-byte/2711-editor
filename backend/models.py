from typing import Literal

from pydantic import BaseModel, Field, field_validator

from document_extract import MAX_CREATE_CHARS


StylePreset = Literal["xianxia", "urban_romance", "mystery", "campus"]

STYLE_LABELS: dict[str, str] = {
    "xianxia": "古风仙侠",
    "urban_romance": "都市言情",
    "mystery": "悬疑推理",
    "campus": "校园青春",
}


class CharacterBrief(BaseModel):
    name: str
    role: str = ""
    trait: str = ""


class StoryBible(BaseModel):
    title: str
    synopsis: str
    setting: str = ""
    tone: str = ""
    characters: list[CharacterBrief] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    plot_beats: list[str] = Field(default_factory=list)


class ChoiceOption(BaseModel):
    id: str
    text: str
    next: str
    consequence_hint: str = ""


class DialogueLine(BaseModel):
    """橙光式单句对白，点击继续推进。"""

    speaker: str = ""
    text: str
    portrait: str = "none"  # none | left | right


class StoryNode(BaseModel):
    id: str
    title: str
    narrative: str = ""
    speaker: str = ""
    mood: str = "neutral"
    image_prompt: str = ""
    lines: list[DialogueLine] = Field(default_factory=list)
    after_lines_next: str = ""
    choices: list[ChoiceOption] = Field(default_factory=list)
    is_ending: bool = False
    ending_type: str = ""


class GamePack(BaseModel):
    title: str
    style: StylePreset
    style_label: str
    synopsis: str
    start_node_id: str = "start"
    nodes: dict[str, StoryNode]
    characters: list[CharacterBrief] = Field(default_factory=list)


class CreateGameRequest(BaseModel):
    text: str = Field(..., min_length=80, max_length=MAX_CREATE_CHARS)
    style: StylePreset = "urban_romance"

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> str:
        return str(v).strip() if v is not None else ""


class ExpandNodeRequest(BaseModel):
    text: str = Field(..., min_length=80, max_length=MAX_CREATE_CHARS)
    style: StylePreset
    game: GamePack
    current_node_id: str
    choice_id: str
