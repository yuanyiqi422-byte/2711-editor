"""本地快速验证 PDF 采样与截取（无需启动服务）。"""

from __future__ import annotations

import io
import sys

from document_extract import (
    LLM_INPUT_CHARS,
    MAX_PDF_PAGES,
    PDF_PAGE_HARD_CAP,
    extract_from_bytes,
    smart_truncate,
    _select_pdf_page_indices,
)


def _make_pdf(page_count: int) -> bytes:
    import fitz

    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"第{i + 1}页 · 风旅物语测试正文。" * 8)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_page_sampling() -> None:
    over = PDF_PAGE_HARD_CAP + 500
    indices, note = _select_pdf_page_indices(over, 0)
    assert len(indices) <= PDF_PAGE_HARD_CAP
    assert 0 in indices
    assert over - 1 in indices
    assert note
    print("page_sampling ok:", len(indices), "pages,", note[:60], "...")


def test_extract_long_pdf() -> None:
    data = _make_pdf(120)
    result = extract_from_bytes(data, "long.pdf")
    assert result.total_pages == 120
    assert result.pages_processed == 120
    assert result.char_count > 1000
    assert len(result.text) == result.char_count
    assert result.llm_char_count == result.char_count
    print(
        "extract_long_pdf ok:",
        result.pages_processed,
        "/",
        result.total_pages,
        "chars",
        result.char_count,
        "truncated",
        result.truncated,
    )


def test_chapter_truncate() -> None:
    parts = []
    for i in range(30):
        parts.append(f"第{i + 1}章\n\n" + ("情节" * 400))
    text = "\n\n".join(parts)
    out, truncated, note = smart_truncate(text, 5000)
    assert truncated
    assert "章" in note
    assert len(out) <= 5000
    print("chapter_truncate ok:", len(out), note[:80], "...")


if __name__ == "__main__":
    test_page_sampling()
    test_extract_long_pdf()
    test_chapter_truncate()
    print("LLM_INPUT_CHARS=", LLM_INPUT_CHARS)
    print("all passed")
