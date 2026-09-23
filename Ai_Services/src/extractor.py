"""
PDF Extraction — 4 strategies with automatic fallback.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    rows: List[List[str]]
    page_number: int
    strategy: str = ""


@dataclass
class ExtractedData:
    tables: List[ExtractedTable]
    full_text: str
    pages_text: List[str]
    page_count: int
    source_file: str


STRATEGIES = {
    "lines": {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "join_tolerance": 4,
    },
    "text": {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "join_tolerance": 5,
        "text_kwargs": {"x_tolerance": 4, "y_tolerance": 4},
    },
    "mixed": {
        "vertical_strategy": "lines",
        "horizontal_strategy": "text",
        "snap_tolerance": 4,
        "join_tolerance": 4,
        "text_kwargs": {"x_tolerance": 4, "y_tolerance": 4},
    },
}


def _clean_rows(raw_rows: list) -> List[List[str]]:
    return [
        [(str(c or "").strip()) for c in row]
        for row in raw_rows
    ]


def _is_useful(rows: List[List[str]], min_rows=2, min_cols=3) -> bool:
    return len(rows) >= min_rows and sum(1 for r in rows if len(r) >= min_cols) >= min_rows


def _try_strategy(page, settings: dict, name: str, page_num: int) -> List[ExtractedTable]:
    try:
        tables = page.extract_tables(table_settings=settings)
        result = []
        for raw in tables:
            cleaned = _clean_rows(raw)
            if _is_useful(cleaned):
                result.append(ExtractedTable(rows=cleaned, page_number=page_num, strategy=name))
        return result
    except Exception:
        return []


def _try_word_clustering(page, page_num: int) -> List[ExtractedTable]:
    """For PDFs with no table structure at all."""
    try:
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=True)
        if not words or len(words) < 10:
            return []

        words.sort(key=lambda w: (round(w["top"], 0), w["x0"]))
        rows, current, cur_y = [], [], None

        for w in words:
            y = round(w["top"], 0)
            if cur_y is None or abs(y - cur_y) <= 6:
                current.append(w["text"])
                cur_y = y
            else:
                if len(current) >= 3:
                    rows.append(current)
                current = [w["text"]]
                cur_y = y
        if len(current) >= 3:
            rows.append(current)

        if _is_useful(rows, min_rows=3, min_cols=2):
            return [ExtractedTable(rows=rows, page_number=page_num, strategy="words")]
    except Exception:
        pass
    return []


def extract_with_pdfplumber(pdf_path: Path) -> ExtractedData:
    logger.info(f"Extracting: {pdf_path.name}")
    all_tables, pages_text, parts = [], [], []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            pages_text.append(text)
            parts.append(text)

            for name, settings in STRATEGIES.items():
                found = _try_strategy(page, settings, name, i)
                if found:
                    all_tables.extend(found)
                    break
            else:
                all_tables.extend(_try_word_clustering(page, i))

    strat_counts = {}
    for t in all_tables:
        strat_counts[t.strategy] = strat_counts.get(t.strategy, 0) + 1
    logger.info(f"Tables: {len(all_tables)} ({strat_counts}), Pages: {len(pages_text)}")

    return ExtractedData(
        tables=all_tables,
        full_text="\n".join(parts),
        pages_text=pages_text,
        page_count=len(pages_text),
        source_file=pdf_path.name,
    )


def extract_with_fitz(pdf_path: Path) -> ExtractedData:
    import fitz
    logger.warning("Fallback: PyMuPDF (text only)")
    texts = []
    doc = fitz.open(str(pdf_path))
    for page in doc:
        texts.append(page.get_text("text") or "")
    doc.close()
    return ExtractedData(
        tables=[], full_text="\n".join(texts),
        pages_text=texts, page_count=len(texts), source_file=pdf_path.name,
    )


def extract_pdf(pdf_path: str | Path) -> ExtractedData:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    try:
        data = extract_with_pdfplumber(pdf_path)
        if data.tables or len(data.full_text) > 100:
            return data
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")
    return extract_with_fitz(pdf_path)