"""Pure-Python PDF splitter for batch invoice documents.

Heuristically detects invoice boundaries by scanning each page for
new invoice keywords (e.g. "Facture", "Invoice", page-1 headers).
When a boundary is found, the current page(s) are flushed into a
sub-PDF and a new one is started.
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

_INVOICE_PATTERNS = [
    re.compile(r"facture\s+r[ée]f", re.IGNORECASE),
    re.compile(r"invoice\s+no", re.IGNORECASE),
    re.compile(r"invoice\s+number", re.IGNORECASE),
    re.compile(r"bill\s+of\s+lading", re.IGNORECASE),
    re.compile(r"page\s+1\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"^\s*invoice\s*$", re.IGNORECASE),
    re.compile(r"bon\s+de\s+livraison", re.IGNORECASE),
]


def _looks_like_new_invoice(text: str) -> bool:
    for pat in _INVOICE_PATTERNS:
        if pat.search(text):
            return True
    return False


def _extract_page_text(reader: PdfReader, page_index: int) -> str:
    try:
        return reader.pages[page_index].extract_text() or ""
    except Exception:
        return ""


def split_pdf(source_path: str | Path, *, output_dir: str | Path | None = None) -> list[str]:
    """Split a multi-invoice PDF into individual single-invoice PDFs.

    Returns a list of absolute paths to the split PDF files.
    If the document appears to be a single invoice, returns a list
    containing only the original path.
    """
    source_path = Path(source_path)
    output_dir = Path(output_dir) if output_dir else source_path.parent / "split"

    reader = PdfReader(str(source_path))
    total_pages = len(reader.pages)

    if total_pages == 1:
        logger.info("split=skip_single_page file=%s", source_path.name)
        return [str(source_path)]

    output_dir.mkdir(parents=True, exist_ok=True)
    split_files: list[str] = []

    writer: PdfWriter | None = None
    page_buffer: list[Any] = []
    invoice_count = 0

    for idx in range(total_pages):
        page = reader.pages[idx]
        page_text = _extract_page_text(reader, idx)
        is_new_invoice = _looks_like_new_invoice(page_text)

        if is_new_invoice and page_buffer:
            # Close the current chunk
            invoice_count += 1
            out_name = f"{source_path.stem}_inv_{invoice_count:03d}{source_path.suffix}"
            out_path = output_dir / out_name
            _write_chunk(page_buffer, out_path)
            split_files.append(str(out_path))
            page_buffer = []

        page_buffer.append(page)

    # Flush the final chunk
    if page_buffer:
        invoice_count += 1
        out_name = f"{source_path.stem}_inv_{invoice_count:03d}{source_path.suffix}"
        out_path = output_dir / out_name
        _write_chunk(page_buffer, out_path)
        split_files.append(str(out_path))

    logger.info(
        "split=complete file=%s total_invoices=%d split_files=%s",
        source_path.name, invoice_count, split_files
    )
    return split_files


def _write_chunk(pages: list[Any], out_path: Path) -> None:
    writer = PdfWriter()
    for page in pages:
        writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)
