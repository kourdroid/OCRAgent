from __future__ import annotations

from src.dossiers.models import DecisionStatus, DossierCaseContext
from src.dossiers.rules import evaluate_ruleset


def _document(document_id: str, value: str) -> dict:
    return {
        "document_id": document_id,
        "document_type": "DUA",
        "facts": [
            {
                "field_path": "declaration_number",
                "value": value,
                "page": 1,
                "source_text": value,
                "confidence": 0.99,
            }
        ],
    }


def _ruleset(outcome: str = "BLOCKED") -> dict:
    return {
        "ruleset_id": "delassus-v2",
        "version": 2,
        "rules": [
            {
                "rule_id": "declaration-match",
                "template_type": "EXACT_MATCH",
                "name": "Declaration number must match",
                "field_path": "declaration_number",
                "severity": "critical",
                "failure_outcome": outcome,
            }
        ],
    }


def test_active_exact_match_rule_blocks_confirmed_mismatch() -> None:
    decision = evaluate_ruleset(
        DossierCaseContext(
            case_id="case-1",
            client_id="delassus",
            documents=[_document("document-1", "123"), _document("document-2", "456")],
        ),
        _ruleset(),
    )

    assert decision.status is DecisionStatus.BLOCKED
    assert decision.ruleset_id == "delassus-v2"
    assert decision.discrepancies[0].rule_id == "declaration-match"


def test_active_ruleset_remains_review_only_without_automatic_clearance() -> None:
    decision = evaluate_ruleset(
        DossierCaseContext(
            case_id="case-1",
            client_id="delassus",
            documents=[_document("document-1", "123"), _document("document-2", "123")],
        ),
        _ruleset(),
    )

    assert decision.status is DecisionStatus.REVIEW_REQUIRED
    assert decision.discrepancies == []
