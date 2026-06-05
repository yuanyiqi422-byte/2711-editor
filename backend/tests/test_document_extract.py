"""Document extract unit tests (ported from test_pdf_extract.py)."""

from __future__ import annotations

import io

from document_extract import (
    LLM_INPUT_CHARS,
    PDF_PAGE_HARD_CAP,
    _select_pdf_page_indices,
    extract_from_bytes,
    smart_truncate,
)


def _make_pdf(page_count: int) -> bytes:
    import fitz

    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"第{i + 1}页 · 2711 Editor 测试正文。" * 8)
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


def test_extract_long_pdf() -> None:
    data = _make_pdf(120)
    result = extract_from_bytes(data, "long.pdf")
    assert result.total_pages == 120
    assert result.pages_processed == 120
    assert result.char_count > 1000
    assert len(result.text) == result.char_count
    assert result.llm_char_count == result.char_count


def test_chapter_truncate() -> None:
    parts = [f"第{i + 1}章\n\n" + ("情节" * 400) for i in range(30)]
    text = "\n\n".join(parts)
    out, truncated, note = smart_truncate(text, 5000)
    assert truncated
    assert "章" in note
    assert len(out) <= 5000


def test_llm_input_chars_is_int() -> None:
    assert isinstance(LLM_INPUT_CHARS, int)
