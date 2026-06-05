from pydantic import BaseModel, Field


class IngestFileResponse(BaseModel):
    text: str
    char_count: int
    truncated: bool
    truncate_note: str = ""
    format: str
    filename: str
    pages_processed: int | None = None
    total_pages: int | None = None
    used_ocr: bool = False
    warnings: list[str] = Field(default_factory=list)
    llm_char_count: int = Field(description="送入 AI 转化的字数")
