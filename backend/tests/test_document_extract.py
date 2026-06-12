"""Document extract unit tests (ported from test_pdf_extract.py)."""

from __future__ import annotations

import io

import pytest

from document_extract import (
    PDF_PAGE_HARD_CAP,
    _select_pdf_page_indices,
    extract_from_bytes,
    prepare_llm_text,
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


def test_page_sampling_unlimited_by_default() -> None:
    assert PDF_PAGE_HARD_CAP == 0
    indices, note = _select_pdf_page_indices(500, 0)
    assert len(indices) == 500
    assert note == ""


def test_page_sampling_when_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("document_extract.PDF_PAGE_HARD_CAP", 200)
    indices, note = _select_pdf_page_indices(500, 0)
    assert len(indices) <= 200
    assert 0 in indices
    assert 499 in indices
    assert note


def test_extract_long_pdf() -> None:
    data = _make_pdf(120)
    result = extract_from_bytes(data, "long.pdf")
    assert result.total_pages == 120
    assert result.pages_processed == 120
    assert result.char_count > 1000
    assert len(result.text) == result.char_count
    assert result.llm_char_count == result.char_count
    assert result.truncated is False


def test_chapter_truncate() -> None:
    parts = [f"第{i + 1}章\n\n" + ("情节" * 400) for i in range(30)]
    text = "\n\n".join(parts)
    out, truncated, note = smart_truncate(text, 5000)
    assert truncated
    assert "章" in note
    assert len(out) <= 5000


def test_prepare_llm_text_unlimited_by_default() -> None:
    text = "字" * 200_000
    out, truncated, note = prepare_llm_text(text)
    assert truncated is False
    assert note == ""
    assert len(out) == len(text)
