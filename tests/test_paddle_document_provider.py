from __future__ import annotations

import pytest

from src.dossiers.models import DocumentType
from src.infrastructure.paddle_document_provider import PaddleDocumentIntelligenceProvider
from src.providers.ocr import OCRDocument, OCRLine, OCRPage


def _line(text: str, *, confidence: float = 0.98) -> OCRLine:
    return OCRLine(
        text=text,
        confidence=confidence,
        bbox=[0.1, 0.2, 0.8, 0.25],
    )


def _document(*pages: list[OCRLine]) -> OCRDocument:
    return OCRDocument(
        pages=[
            OCRPage(page=index, width=1000, height=1400, lines=lines)
            for index, lines in enumerate(pages, start=1)
        ]
    )


class _OCR:
    provider_id = "test-ocr"
    model_id = "test-model"

    def __init__(self, document: OCRDocument) -> None:
        self.document = document
        self.calls = 0

    async def healthcheck(self):
        return {"ok": True}

    async def recognize_pdf(self, _pdf_bytes: bytes) -> OCRDocument:
        self.calls += 1
        return self.document


@pytest.mark.asyncio
async def test_classifies_and_groups_supplier_pages() -> None:
    ocr = _OCR(
        _document(
            [_line("Factura"), _line("ONDUPET, S.L.")],
            [_line("Packing List"), _line("ONDUPET S.L.")],
            [_line("Albarán"), _line("ONDUPET, S.L.")],
            [_line("INTERNATIONAL CONSIGNMENT NOTE"), _line("ONDUPET, S.L.")],
        )
    )
    provider = PaddleDocumentIntelligenceProvider(ocr)

    result = await provider.classify_pdf(
        b"%PDF-supplier",
        page_count=4,
        supported_types=frozenset(DocumentType),
    )

    assert len(result.segments) == 1
    assert result.segments[0].document_type is DocumentType.SUPPLIER_DOCUMENT
    assert result.segments[0].page_start == 1
    assert result.segments[0].page_end == 4


@pytest.mark.asyncio
async def test_unknown_page_stays_conservative() -> None:
    provider = PaddleDocumentIntelligenceProvider(
        _OCR(_document([_line("Unrecognized content")]))
    )

    result = await provider.classify_pdf(
        b"%PDF-unknown",
        page_count=1,
        supported_types=frozenset(DocumentType),
    )

    assert result.segments[0].document_type is DocumentType.UNKNOWN
    assert result.segments[0].confidence == 0.0


@pytest.mark.asyncio
async def test_bad_extraction_preserves_values_and_evidence() -> None:
    ocr = _OCR(
        _document(
            [
                _line("Bon à délivrer"),
                _line("Numéro du BAD : 411260000216751"),
                _line("N° Connaissement : 77"),
                _line("N° du DS : 41100020260005509M"),
                _line("Navire : WASA EXPRESS"),
                _line("Poids Totale(KG): 5822.0"),
                _line("Equipement 767208/48956B40"),
            ]
        )
    )
    provider = PaddleDocumentIntelligenceProvider(ocr)

    extraction = await provider.extract_pdf(
        b"%PDF-bad",
        document_type=DocumentType.BAD,
        allowed_fields=(
            "dossier_reference",
            "bill_of_lading_number",
            "container_number",
            "vessel_name",
        ),
    )

    facts = {fact.field_path: fact for fact in extraction.facts}
    assert facts["dossier_reference"].value == "41100020260005509M"
    assert facts["bill_of_lading_number"].value == "77"
    assert facts["container_number"].value == "767208"
    assert facts["vessel_name"].value == "WASA EXPRESS"
    assert facts["bill_of_lading_number"].bbox == [0.1, 0.2, 0.8, 0.25]
    assert facts["bill_of_lading_number"].source_text == "N° Connaissement : 77"


@pytest.mark.asyncio
async def test_reuses_ocr_for_classification_and_single_segment_extraction() -> None:
    ocr = _OCR(
        _document(
            [
                _line("Bon à délivrer"),
                _line("Numéro du BAD : 411260000216751"),
                _line("N° Connaissement : 77"),
            ]
        )
    )
    provider = PaddleDocumentIntelligenceProvider(ocr)
    pdf = b"%PDF-same-document"

    await provider.classify_pdf(
        pdf,
        page_count=1,
        supported_types=frozenset(DocumentType),
    )
    await provider.extract_pdf(
        pdf,
        document_type=DocumentType.BAD,
        allowed_fields=("bill_of_lading_number",),
    )

    assert ocr.calls == 1


@pytest.mark.asyncio
async def test_bill_of_lading_uses_value_lines_not_labels() -> None:
    provider = PaddleDocumentIntelligenceProvider(
        _OCR(
            _document(
                [
                    _line("B/L Nº"),
                    _line("077"),
                    _line("Navire / Vessel"),
                    _line("Port de chargement"),
                    _line("ALGECIRAS"),
                    _line("WASA EXPRESS"),
                ]
            )
        )
    )

    extraction = await provider.extract_pdf(
        b"%PDF-bl",
        document_type=DocumentType.BILL_OF_LADING,
        allowed_fields=("bill_of_lading_number", "vessel_name"),
    )

    facts = {fact.field_path: fact.value for fact in extraction.facts}
    assert facts == {
        "bill_of_lading_number": "077",
        "vessel_name": "WASA EXPRESS",
    }
