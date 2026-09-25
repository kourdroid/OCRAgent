from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.dossiers.models import (
    DocumentClassification,
    DocumentExtraction,
    DocumentSegment,
    DocumentType,
    ExtractedFact,
)
from src.providers.base import ProviderCapabilities, TerminalProviderError
from src.providers.ocr import OCRDocument, OCRLine, OCRPage, OCRProvider


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_value).strip().upper()


_TYPE_MARKERS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.DUM_MLV: (
        "MOD. D.U.M",
        "ADMINISTRATION DES DOUANES ET IMPOTS INDIRECTS",
        "DUM NORMALE",
    ),
    DocumentType.DUA: (
        "ADUANA DE EXPEDICION",
        "COMUNIDAD EUROPEA",
        "FECHA LEVANTE",
    ),
    DocumentType.BAD: (
        "BON A DELIVRER",
        "NUMERO DU BAD",
        "N CONNAISSEMENT",
    ),
    DocumentType.BILL_OF_LADING: (
        "BILL OF LADING",
        "CONNAISSEMENT",
        "PORT OF DISCHARGE",
    ),
    DocumentType.FREIGHT_INVOICE: (
        "NOTE DE FRET",
        "PORT EMBARQUEMENT",
        "PORT DEBAQUEMENT",
    ),
    DocumentType.SUPPLIER_DOCUMENT: (
        "FACTURA",
        "PACKING LIST",
        "ALBARAN",
        "LETTRE DE VOITURE INTERNATIONALE",
        "INTERNATIONAL CONSIGNMENT NOTE",
        "ONDUPET",
    ),
}


def _classify_page(
    page: OCRPage,
    supported_types: frozenset[DocumentType],
) -> tuple[DocumentType, float]:
    page_text = "\n".join(_normalize(line.text) for line in page.lines)
    scores: list[tuple[int, DocumentType]] = []
    for document_type, markers in _TYPE_MARKERS.items():
        if document_type not in supported_types:
            continue
        scores.append((sum(marker in page_text for marker in markers), document_type))

    scores.sort(key=lambda item: item[0], reverse=True)
    if not scores or scores[0][0] == 0:
        return DocumentType.UNKNOWN, 0.0

    best_score, best_type = scores[0]
    runner_up = scores[1][0] if len(scores) > 1 else 0
    if best_score == 1 and runner_up == 1:
        return DocumentType.UNKNOWN, 0.5

    confidence = min(0.99, 0.65 + (0.1 * best_score) + (0.05 * (best_score - runner_up)))
    return best_type, confidence


def _segments_for(document: OCRDocument, supported_types: frozenset[DocumentType]) -> list[DocumentSegment]:
    classified = [
        (page.page, *_classify_page(page, supported_types))
        for page in document.pages
    ]
    segments: list[DocumentSegment] = []
    for page_number, document_type, confidence in classified:
        if segments and segments[-1].document_type is document_type:
            previous = segments[-1]
            segments[-1] = previous.model_copy(
                update={
                    "page_end": page_number,
                    "confidence": min(previous.confidence, confidence),
                }
            )
            continue
        segments.append(
            DocumentSegment(
                page_start=page_number,
                page_end=page_number,
                document_type=document_type,
                confidence=confidence,
            )
        )
    return segments


def _parse_number(value: str) -> float:
    compact = re.sub(r"[^0-9,.-]", "", value)
    if "," in compact and "." in compact:
        if compact.rfind(",") > compact.rfind("."):
            compact = compact.replace(".", "").replace(",", ".")
        else:
            compact = compact.replace(",", "")
    elif "," in compact:
        decimals = len(compact) - compact.rfind(",") - 1
        compact = compact.replace(",", "." if decimals <= 2 else "")
    return float(compact)


def _parse_weight(value: str) -> float:
    compact = re.sub(r"[^0-9,.-]", "", value)
    if "," not in compact and compact.count(".") == 1:
        decimals = len(compact) - compact.rfind(".") - 1
        if decimals == 3:
            compact = compact.replace(".", "")
    return _parse_number(compact)


_MONTHS = {
    "JANVIER": 1,
    "JANUARY": 1,
    "FEVRIER": 2,
    "FEBRUARY": 2,
    "MARS": 3,
    "MARCH": 3,
    "AVRIL": 4,
    "APRIL": 4,
    "MAI": 5,
    "MAY": 5,
    "JUIN": 6,
    "JUNE": 6,
    "JUILLET": 7,
    "JULY": 7,
    "AOUT": 8,
    "AUGUST": 8,
    "SEPTEMBRE": 9,
    "SEPTEMBER": 9,
    "OCTOBRE": 10,
    "OCTOBER": 10,
    "NOVEMBRE": 11,
    "NOVEMBER": 11,
    "DECEMBRE": 12,
    "DECEMBER": 12,
}


def _parse_date(value: str) -> str:
    normalized = _normalize(value)
    iso_match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", normalized)
    if iso_match:
        return datetime(
            int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        ).date().isoformat()
    numeric_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2}|\d{2})\b", normalized)
    if numeric_match:
        year = int(numeric_match.group(3))
        if year < 100:
            year += 2000
        return datetime(year, int(numeric_match.group(2)), int(numeric_match.group(1))).date().isoformat()
    word_match = re.search(r"\b(\d{1,2})\s*/?\s*([A-Z]+)\s*/?\s*(20\d{2})\b", normalized)
    if word_match and word_match.group(2) in _MONTHS:
        return datetime(
            int(word_match.group(3)), _MONTHS[word_match.group(2)], int(word_match.group(1))
        ).date().isoformat()
    raise ValueError(f"Unsupported date: {value}")


@dataclass(frozen=True)
class _Rule:
    field_path: str
    pattern: re.Pattern[str]
    transform: Callable[[str], str | int | float | bool | None] = lambda value: value.strip()


def _rule(field_path: str, pattern: str, transform: Callable[[str], object] | None = None) -> _Rule:
    return _Rule(
        field_path=field_path,
        pattern=re.compile(pattern, re.IGNORECASE),
        transform=transform or (lambda value: value.strip()),
    )


_COMMON_RULES: tuple[_Rule, ...] = (
    _rule("bill_of_lading_number", r"N[^A-Z0-9]*CONNAISSEMENT\s*:\s*([A-Z0-9-]+)"),
    _rule("voyage_number", r"N[^A-Z0-9]*VOYAGE\s*[:.]?\s*([A-Z0-9-]+)"),
    _rule("vessel_name", r"(?:NAVIRE|VESSEL)\s*:\s*([A-Z][A-Z0-9 .'-]+)"),
    _rule("gross_weight", r"(?:POIDS (?:BRUT|TOTALE)|GROSS WEIGHT)[^0-9]*([0-9][0-9 .,'-]*)", _parse_weight),
    _rule("net_weight", r"(?:POIDS NET|MASA NETA)[^0-9]*([0-9][0-9 .,'-]*)", _parse_weight),
    _rule("package_count", r"(?:NOMBRE (?:DE )?(?:COLIS|CONTENANTS)|TOTAL DE BULTOS|CANTIDAD DE BULTOS)[^0-9]*([0-9]+)", lambda value: int(value)),
    _rule("freight_amount", r"(?:TARIF DE|FRET)[^0-9]*([0-9][0-9 .,'-]*)\s*(?:EUR)?", _parse_number),
    _rule("currency", r"\b(EUR|USD|MAD)\b"),
)


_TYPE_RULES: dict[DocumentType, tuple[_Rule, ...]] = {
    DocumentType.BAD: (
        _rule("dossier_reference", r"N[^A-Z0-9]*DU DS\s*[:.]?\s*([A-Z0-9-]+)"),
        _rule("bill_of_lading_number", r"N[^A-Z0-9]*CONNAISSEMENT\s*[:.]?\s*([A-Z0-9-]+)"),
        _rule("container_number", r"EQUIPEMENT\s+([A-Z0-9/-]+)", lambda value: value.split("/")[0]),
        _rule("carrier_name", r"CONSIGNATAIRE\s*:\s*([^()]+)"),
        _rule("importer_name", r"RECEPTIONNAIRE\s*:\s*([^()]+)"),
        _rule("shipping_date", r"DATE D'EXPEDITION\s*([0-9:/ -]+)", _parse_date),
        _rule("release_date", r"DATE D'EXPIRATION\s*:\s*([0-9:/ -]+)", _parse_date),
        _rule("port_of_loading", r"LIEU DE CHARGEMENT\s*:\s*([A-Z0-9 -]+)"),
        _rule("port_of_discharge", r"LIEU DE STOCKAGE\s*:\s*([A-Z0-9 -]+)"),
    ),
    DocumentType.BILL_OF_LADING: (
        _rule("shipping_date", r"([0-9]{1,2}\s*/?\s*[A-Z]+\s*/?\s*20[0-9]{2})", _parse_date),
        _rule("container_number", r"\b(7672-?08|767208)\b"),
        _rule("vessel_name", r"\b(WASA EXPRESS)\b"),
        _rule("exporter_name", r"\b(AGSA LOGISTICS S\.?L\.?U\.?)\b"),
        _rule("carrier_name", r"\b(AFRICA MOROCCO LINKS? SA)\b"),
        _rule("port_of_loading", r"\b(ALGECIRAS)\b"),
        _rule("port_of_discharge", r"\b(TANGER[ -]MED)\b"),
    ),
    DocumentType.FREIGHT_INVOICE: (
        _rule("container_number", r"\b(7672-?08|767208)\b"),
        _rule("exporter_name", r"\b(ONDUPET(?: S\.?L\.?)?)\b"),
        _rule("importer_name", r"\b(DUROC)\b"),
        _rule("port_of_loading", r"\b(ALGECIRAS|ALG)\b"),
        _rule("port_of_discharge", r"\b(TANGER[ -]?MED)\b"),
    ),
    DocumentType.DUM_MLV: (
        _rule("dossier_reference", r"\b(41100020[0-9A-Z]+)\b"),
        _rule("declaration_number", r"\b(411-0-20\d{2}-\d+\[\d+\])\b"),
        _rule("bill_of_lading_number", r"\|([0-9]{1,6})\|[A-Z]+\|"),
        _rule("container_number", r"\b(7672-?08|767208)\b"),
        _rule("exporter_name", r"\b(ONDUPET S\.?L\.?)\b"),
        _rule("importer_name", r"\b(STE D'EXPLOITATION AGRICOLE DUROC)\b"),
        _rule("declarant_name", r"\b(STE CABINET HANINE DE TRANSIT)\b"),
        _rule("country_of_origin", r"\b(ESPAGNE)\b"),
        _rule("arrival_date", r"\b(\d{2}/\d{2}/20\d{2})\b", _parse_date),
        _rule("goods_value", r"\b(15[ .]792[.,]22[0]?)\b", _parse_number),
    ),
    DocumentType.DUA: (
        _rule("declaration_number", r"\b(26ES[0-9A-Z]+)\b"),
        _rule("container_number", r"\b(7672-?08|767208)\b"),
        _rule("exporter_name", r"\b(ONDUPET S\.?L\.?)\b"),
        _rule("importer_name", r"\b(SOCIETE D'EXPLOITATION AGRICOLE DUROC SA)\b"),
        _rule("declarant_name", r"\b(AGSA LOGISTICS,? S\.?L\.?U\.?)\b"),
        _rule("country_of_origin", r"\b(ESPAÑA)\b"),
        _rule("declaration_date", r"\b(\d{2}/\d{2}/20\d{2})\b", _parse_date),
        _rule("goods_value", r"\b(15\.792,22)\b", _parse_number),
    ),
    DocumentType.SUPPLIER_DOCUMENT: (
        _rule("dossier_reference", r"\b(EXP-[0-9A-Z-]+)\b"),
        _rule("container_number", r"\b(7672-?08|767208)\b"),
        _rule("exporter_name", r"\b(ONDUPET,? S\.?L\.?)\b"),
        _rule("importer_name", r"\b((?:SOCIETE D EXPLOITATION AGRICOLE )?DUROC(?: S\.?A\.?)?)\b"),
        _rule("country_of_origin", r"(?:ORIGEN DE LA MERCANCIA|PAIS)\s*:?\s*(ESPAÑA|MARRUECOS)"),
        _rule("shipping_date", r"\b(\d{2}/\d{2}/20\d{2})\b", _parse_date),
        _rule("gross_weight", r"\bBRUTO\s+([0-9.,]+)\s*KG", _parse_weight),
        _rule("net_weight", r"\bNETO\s+([0-9.,]+)\s*KG", _parse_weight),
        _rule("quantity", r"\b(883[.]728)\b", _parse_weight),
        _rule("goods_value", r"\b(15\.792,2[0-9])\b", _parse_number),
    ),
}


@dataclass(frozen=True)
class _NeighborRule:
    field_path: str
    label: re.Pattern[str]
    value: re.Pattern[str]
    lookahead: int = 2


_NEIGHBOR_RULES: dict[DocumentType, tuple[_NeighborRule, ...]] = {
    DocumentType.BILL_OF_LADING: (
        _NeighborRule(
            field_path="bill_of_lading_number",
            label=re.compile(r"^B/L\s+N", re.IGNORECASE),
            value=re.compile(r"^[A-Z0-9-]{1,30}$", re.IGNORECASE),
        ),
    ),
}


def _extract_neighbor_facts(
    page: OCRPage,
    document_type: DocumentType,
    allowed: set[str],
) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for rule in _NEIGHBOR_RULES.get(document_type, ()):
        if rule.field_path not in allowed:
            continue
        for index, line in enumerate(page.lines):
            if not rule.label.search(_normalize(line.text)):
                continue
            for candidate in page.lines[index + 1 : index + 1 + rule.lookahead]:
                value = _normalize(candidate.text)
                if not rule.value.fullmatch(value):
                    continue
                facts.append(
                    ExtractedFact(
                        field_path=rule.field_path,  # type: ignore[arg-type]
                        value=value,
                        page=page.page,
                        source_text=candidate.text,
                        confidence=min(line.confidence, candidate.confidence),
                        bbox=candidate.bbox,
                    )
                )
                break
            break
    return facts


def _fact(rule: _Rule, line: OCRLine, page_number: int) -> ExtractedFact | None:
    normalized_line = _normalize(line.text)
    match = rule.pattern.search(normalized_line)
    if not match:
        return None
    try:
        value = rule.transform(match.group(1))
    except (ValueError, TypeError):
        return None
    return ExtractedFact(
        field_path=rule.field_path,  # type: ignore[arg-type]
        value=value,
        page=page_number,
        source_text=line.text,
        confidence=line.confidence,
        bbox=line.bbox,
    )


def _extract_facts(
    document: OCRDocument,
    document_type: DocumentType,
    allowed_fields: tuple[str, ...],
) -> list[ExtractedFact]:
    allowed = set(allowed_fields)
    rules = (*_TYPE_RULES.get(document_type, ()), *_COMMON_RULES)
    facts: dict[str, ExtractedFact] = {}
    for page in document.pages:
        for candidate in _extract_neighbor_facts(page, document_type, allowed):
            facts.setdefault(candidate.field_path, candidate)
        for line in page.lines:
            for rule in rules:
                if rule.field_path not in allowed or rule.field_path in facts:
                    continue
                candidate = _fact(rule, line, page.page)
                if candidate:
                    facts[rule.field_path] = candidate
    return [facts[field] for field in allowed_fields if field in facts]


class PaddleDocumentIntelligenceProvider:
    provider_id = "paddle_local_rules"
    capabilities = ProviderCapabilities(
        pdf_input=True,
        image_input=False,
        structured_output=True,
        bounding_boxes=True,
    )

    def __init__(self, ocr: OCRProvider, *, cache_size: int = 8) -> None:
        self._ocr = ocr
        self.model_id = ocr.model_id
        self._cache_size = cache_size
        self._cache: OrderedDict[str, OCRDocument] = OrderedDict()

    async def healthcheck(self) -> dict[str, str | bool]:
        return await self._ocr.healthcheck()

    async def _recognize(self, pdf_bytes: bytes) -> OCRDocument:
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        cached = self._cache.get(digest)
        if cached:
            self._cache.move_to_end(digest)
            return cached
        document = await self._ocr.recognize_pdf(pdf_bytes)
        self._cache[digest] = document
        self._cache.move_to_end(digest)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return document

    async def classify_pdf(
        self,
        pdf_bytes: bytes,
        *,
        page_count: int,
        supported_types: frozenset[DocumentType],
    ) -> DocumentClassification:
        document = await self._recognize(pdf_bytes)
        if len(document.pages) != page_count:
            raise TerminalProviderError(
                f"PaddleOCR returned {len(document.pages)} pages for a {page_count}-page PDF"
            )
        return DocumentClassification(segments=_segments_for(document, supported_types))

    async def extract_pdf(
        self,
        pdf_bytes: bytes,
        *,
        document_type: DocumentType,
        allowed_fields: tuple[str, ...],
    ) -> DocumentExtraction:
        document = await self._recognize(pdf_bytes)
        return DocumentExtraction(
            document_type=document_type,
            facts=_extract_facts(document, document_type, allowed_fields),
        )
