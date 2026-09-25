from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.dossiers.models import (
    ComparedValue,
    DecisionStatus,
    DossierCaseContext,
    DossierDecision,
    DossierDiscrepancy,
    EvidenceReference,
)


def _normalize(value: Any) -> str:
    return "" if value is None else "".join(str(value).upper().split())


def _compared_values(case_context: DossierCaseContext, field_path: str) -> list[ComparedValue]:
    values: list[ComparedValue] = []
    for document in case_context.documents:
        for fact in document.get("facts") or []:
            if fact.get("field_path") != field_path:
                continue
            values.append(
                ComparedValue(
                    document_id=str(document["document_id"]),
                    field_path=field_path,
                    value=fact.get("value"),
                    evidence=EvidenceReference(
                        document_id=str(document["document_id"]),
                        field_path=field_path,
                        page=int(fact["page"]),
                        source_text=str(fact["source_text"]),
                        confidence=float(fact["confidence"]),
                        bbox=fact.get("bbox"),
                    ),
                )
            )
    return values


def evaluate_ruleset(case_context: DossierCaseContext, ruleset: dict[str, Any]) -> DossierDecision:
    """Evaluate only supported templates; an unknown or incomplete rule stays review-only."""
    discrepancies: list[DossierDiscrepancy] = []
    requires_review = False
    blocked = False

    for rule in ruleset.get("rules", []):
        if not rule.get("is_active", True):
            continue
        template = rule["template_type"]
        rule_id = str(rule["rule_id"])
        severity = rule.get("severity", "warning")
        outcome = rule.get("failure_outcome", "REVIEW_REQUIRED")
        field_path = rule.get("field_path")

        if template == "REQUIRED_DOCUMENT":
            required_type = rule.get("parameters", {}).get("document_type")
            present = any(doc.get("document_type") == required_type for doc in case_context.documents)
            if present:
                continue
            message = f"Required document type {required_type or 'unknown'} is missing."
            values: list[ComparedValue] = []
        elif template in {"FIELD_REQUIRED", "EXACT_MATCH", "AUTHORITY_PRECEDENCE"}:
            values = _compared_values(case_context, str(field_path or ""))
            normalized = {_normalize(item.value) for item in values if _normalize(item.value)}
            if template == "FIELD_REQUIRED":
                if normalized:
                    continue
                message = f"Required field {field_path or 'unknown'} has no evidence-backed value."
            elif template == "EXACT_MATCH":
                if len(normalized) == 1:
                    continue
                message = (
                    f"{field_path or 'Field'} is missing or differs across supporting documents."
                )
            else:
                # Authority rules require explicit confirmed document types. Until then, retain review.
                parameters = rule.get("parameters", {})
                authority = parameters.get("authoritative_document_type")
                if not authority:
                    requires_review = True
                    discrepancies.append(DossierDiscrepancy(
                        rule_id=rule_id,
                        severity="warning",
                        message=f"{rule.get('name', rule_id)} lacks a confirmed authoritative source.",
                        values=values,
                    ))
                    continue
                authority_values = [item for item in values if any(
                    doc.get("document_id") == item.document_id and doc.get("document_type") == authority
                    for doc in case_context.documents
                )]
                if len({_normalize(item.value) for item in authority_values if _normalize(item.value)}) == 1:
                    continue
                message = f"{field_path or 'Field'} has no unambiguous value from {authority}."
        else:
            # Numeric/date rules need client-provided parameters. They are deliberately conservative.
            requires_review = True
            discrepancies.append(DossierDiscrepancy(
                rule_id=rule_id,
                severity="warning",
                message=f"{rule.get('name', rule_id)} requires configured evaluator parameters.",
            ))
            continue

        discrepancies.append(DossierDiscrepancy(
            rule_id=rule_id,
            severity=severity,
            message=message,
            values=values,
        ))
        if outcome == "BLOCKED":
            blocked = True
        else:
            requires_review = True

    if blocked:
        status = DecisionStatus.BLOCKED
        summary = "A confirmed active rule found a blocking discrepancy."
    else:
        # Delassus must explicitly opt into automatic clearance in a later confirmed rule version.
        status = DecisionStatus.REVIEW_REQUIRED
        summary = "The dossier requires human review under the active Delassus ruleset."
        requires_review = True

    return DossierDecision(
        status=status,
        ruleset_id=str(ruleset["ruleset_id"]),
        ruleset_version=str(ruleset["version"]),
        discrepancies=discrepancies,
        summary=summary,
    )
