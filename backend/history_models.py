from pydantic import BaseModel, Field

from document_extract import MAX_CREATE_CHARS
from models import GamePack, StylePreset

_HISTORY_TEXT_KW: dict = {"min_length": 1}
if MAX_CREATE_CHARS > 0:
    _HISTORY_TEXT_KW["max_length"] = MAX_CREATE_CHARS


class HistorySaveRequest(BaseModel):
    text: str = Field(**_HISTORY_TEXT_KW)
    filename: str | None = None
    style: StylePreset = "urban_romance"
    title: str | None = None
    game: GamePack | None = None
    entry_id: str | None = None


class HistoryItem(BaseModel):
    id: str
    title: str
    filename: str | None = None
    style: str
    char_count: int
    created_at: str
    updated_at: str
    has_game: bool = False
    node_count: int = 0
    ending_count: int = 0
    branch_count: int = 0
    unlocked_endings: int = 0
    share_token: str | None = None


class HistoryProgress(BaseModel):
    unlocked: list[dict] = Field(default_factory=list)
    checkpoint: dict | None = None


class HistoryDetail(BaseModel):
    item: HistoryItem
    text: str
    game: GamePack | None = None
    progress: HistoryProgress | None = None
