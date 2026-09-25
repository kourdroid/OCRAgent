from __future__ import annotations

from src.dossiers.models import (
    DecisionStatus,
    DocumentSegment,
    DocumentType,
    DossierCaseContext,
)
from src.dossiers.processor import normalize_segments
from src.plugins.morocco_import import MoroccoImportDossierWorkflow


def _document(
    document_id: str,
    document_type: DocumentType,
    field_path: str,
    value: str,
    *,
    confidence: float = 0.99,
) -> dict:
    return {
        "document_id": document_id,
        "document_type": document_type.value,
        "facts": [
            {
                "field_path": field_path,
                "value": value,
                "page": 1,
                "source_text": value,
                "confidence": confidence,
                "bbox": [0.1, 0.1, 0.3, 0.2],
            }
        ],
    }


def test_identifier_mismatch_blocks_with_evidence() -> None:
    workflow = MoroccoImportDossierWorkflow()
    context = DossierCaseContext(
        case_id="case-1",
        client_id="delassus",
        documents=[
            _document(
                "doc-1",
                DocumentType.DUM_MLV,
                "bill_of_lading_number",
                "BL-100",
            ),
            _document(
                "doc-2",
                DocumentType.BILL_OF_LADING,
                "bill_of_lading_number",
                "BL-200",
            ),
        ],
    )

    decision = workflow.reconcile(context)

    assert decision.status is DecisionStatus.BLOCKED
    assert decision.discrepancies[0].rule_id == "IDENTITY-BILL_OF_LADING_NUMBER"
    assert {value.document_id for value in decision.discrepancies[0].values} == {
        "doc-1",
        "doc-2",
    }


def test_bill_of_lading_leading_zeroes_do_not_create_false_mismatch() -> None:
    workflow = MoroccoImportDossierWorkflow()
    context = DossierCaseContext(
        case_id="case-1",
        client_id="delassus",
        documents=[
            _document(
                "doc-1",
                DocumentType.DUM_MLV,
                "bill_of_lading_number",
                "77",
            ),
            _document(
                "doc-2",
                DocumentType.BILL_OF_LADING,
                "bill_of_lading_number",
                "077",
            ),
        ],
    )

    decision = workflow.reconcile(context)

    assert decision.status is DecisionStatus.REVIEW_REQUIRED
    assert not any(
        item.rule_id == "IDENTITY-BILL_OF_LADING_NUMBER"
        for item in decision.discrepancies
    )


def test_unconfirmed_pilot_rules_never_auto_clear() -> None:
    workflow = MoroccoImportDossierWorkflow(allow_automatic_ready=False)
    context = DossierCaseContext(
        case_id="case-1",
        client_id="delassus",
        documents=[
            _document(
                "doc-1",
                DocumentType.BILL_OF_LADING,
                "bill_of_lading_number",
                "BL-100",
            )
        ],
    )

    decision = workflow.reconcile(context)

    assert decision.status is DecisionStatus.REVIEW_REQUIRED


def test_unknown_document_requires_review() -> None:
    workflow = MoroccoImportDossierWorkflow(allow_automatic_ready=True)
    context = DossierCaseContext(
        case_id="case-1",
        client_id="delassus",
        documents=[
            {
                "document_id": "doc-1",
                "document_type": DocumentType.UNKNOWN.value,
                "facts": [],
            }
        ],
    )

    decision = workflow.reconcile(context)

    assert decision.status is DecisionStatus.REVIEW_REQUIRED
    assert {item.rule_id for item in decision.discrepancies} == {
        "DOC-TYPE-UNKNOWN",
        "DOC-FACTS-MISSING",
    }


def test_invalid_page_coverage_falls_back_to_unknown() -> None:
    result = normalize_segments(
        [
            DocumentSegment(
                page_start=1,
                page_end=1,
                document_type=DocumentType.DUM_MLV,
                confidence=0.99,
            ),
            DocumentSegment(
                page_start=3,
                page_end=3,
                document_type=DocumentType.BAD,
                confidence=0.99,
            ),
        ],
        page_count=3,
    )

    assert result == [
        DocumentSegment(
            page_start=1,
            page_end=3,
            document_type=DocumentType.UNKNOWN,
            confidence=0.0,
        )
    ]


def test_low_confidence_type_becomes_unknown_without_losing_page_range() -> None:
    result = normalize_segments(
        [
            DocumentSegment(
                page_start=1,
                page_end=2,
                document_type=DocumentType.DUA,
                confidence=0.5,
            )
        ],
        page_count=2,
    )

    assert result[0].document_type is DocumentType.UNKNOWN
    assert result[0].page_start == 1
    assert result[0].page_end == 2
