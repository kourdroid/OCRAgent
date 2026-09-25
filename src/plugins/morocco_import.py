from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.dossiers.models import (
    ComparedValue,
    DecisionStatus,
    DocumentType,
    DossierCaseContext,
    DossierDecision,
    DossierDiscrepancy,
    EvidenceReference,
)


SUPPORTED_DOCUMENT_TYPES = frozenset(DocumentType)

DOCUMENT_FACTS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.DUM_MLV: (
        "dossier_reference",
        "declaration_number",
        "bill_of_lading_number",
        "container_number",
        "importer_name",
        "exporter_name",
        "country_of_origin",
        "declaration_date",
        "package_count",
        "gross_weight",
        "net_weight",
        "goods_value",
        "freight_amount",
        "currency",
    ),
    DocumentType.DUA: (
        "dossier_reference",
        "declaration_number",
        "bill_of_lading_number",
        "container_number",
        "importer_name",
        "declarant_name",
        "declaration_date",
        "release_date",
    ),
    DocumentType.BAD: (
        "dossier_reference",
        "bill_of_lading_number",
        "container_number",
        "carrier_name",
        "release_date",
    ),
    DocumentType.BILL_OF_LADING: (
        "bill_of_lading_number",
        "container_number",
        "voyage_number",
        "vessel_name",
        "importer_name",
        "exporter_name",
        "carrier_name",
        "port_of_loading",
        "port_of_discharge",
        "shipping_date",
        "arrival_date",
        "package_count",
        "gross_weight",
    ),
    DocumentType.FREIGHT_INVOICE: (
        "dossier_reference",
        "bill_of_lading_number",
        "carrier_name",
        "freight_amount",
        "currency",
    ),
    DocumentType.SUPPLIER_DOCUMENT: (
        "dossier_reference",
        "bill_of_lading_number",
        "importer_name",
        "exporter_name",
        "package_count",
        "gross_weight",
        "net_weight",
        "quantity",
        "goods_value",
        "currency",
    ),
    DocumentType.UNKNOWN: (),
}

EXACT_IDENTITY_FIELDS = (
    "declaration_number",
    "bill_of_lading_number",
    "container_number",
)


def _normalize_identifier(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _normalize_identity(field_path: str, value: object) -> str:
    normalized = _normalize_identifier(value)
    if field_path == "bill_of_lading_number" and normalized.isdigit():
        return normalized.lstrip("0") or "0"
    return normalized


def _as_compared_value(document: dict[str, Any], fact: dict[str, Any]) -> ComparedValue:
    return ComparedValue(
        document_id=str(document["document_id"]),
        field_path=str(fact["field_path"]),
        value=fact.get("value"),
        evidence=EvidenceReference(
            document_id=str(document["document_id"]),
            field_path=str(fact["field_path"]),
            page=int(fact["page"]),
            source_text=str(fact["source_text"]),
            confidence=float(fact["confidence"]),
            bbox=fact.get("bbox"),
        ),
    )


@dataclass(frozen=True)
class MoroccoImportDossierWorkflow:
    workflow_id: str = "morocco_import_dossier"
    workflow_version: str = "1"
    ruleset_id: str = "delassus_pilot"
    ruleset_version: str = "1"
    minimum_confidence: float = 0.85
    allow_automatic_ready: bool = False
    supported_document_types: frozenset[DocumentType] = SUPPORTED_DOCUMENT_TYPES

    def validate_document_types(
        self,
        document_types: list[DocumentType],
    ) -> list[str]:
        return [
            f"Unsupported document type: {document_type}"
            for document_type in document_types
            if document_type not in self.supported_document_types
        ]

    def schema_for(self, document_type: DocumentType) -> tuple[str, ...]:
        return DOCUMENT_FACTS[document_type]

    def reconcile(self, case_context: DossierCaseContext) -> DossierDecision:
        discrepancies: list[DossierDiscrepancy] = []
        facts_by_path: dict[str, list[ComparedValue]] = {}
        requires_review = False

        for document in case_context.documents:
            document_type = DocumentType(document.get("document_type", DocumentType.UNKNOWN))
            if document_type is DocumentType.UNKNOWN:
                requires_review = True
                discrepancies.append(
                    DossierDiscrepancy(
                        rule_id="DOC-TYPE-UNKNOWN",
                        severity="warning",
                        message="A document or page range requires manual classification.",
                    )
                )

            facts = document.get("facts") or []
            if not facts:
                requires_review = True
                discrepancies.append(
                    DossierDiscrepancy(
                        rule_id="DOC-FACTS-MISSING",
                        severity="warning",
                        message=f"No normalized facts were extracted from {document_type}.",
                    )
                )

            for fact in facts:
                compared = _as_compared_value(document, fact)
                facts_by_path.setdefault(compared.field_path, []).append(compared)
                if compared.evidence.confidence < self.minimum_confidence:
                    requires_review = True

        for field_path in EXACT_IDENTITY_FIELDS:
            values = facts_by_path.get(field_path, [])
            normalized_values = {
                _normalize_identity(field_path, value.value)
                for value in values
                if _normalize_identity(field_path, value.value)
            }
            if len(normalized_values) > 1:
                discrepancies.append(
                    DossierDiscrepancy(
                        rule_id=f"IDENTITY-{field_path.upper()}",
                        severity="critical",
                        message=f"Conflicting {field_path.replace('_', ' ')} values were found.",
                        values=values,
                    )
                )

        critical_mismatch = any(item.severity == "critical" for item in discrepancies)
        if critical_mismatch:
            status = DecisionStatus.BLOCKED
            summary = "The dossier contains a confirmed critical identifier mismatch."
        elif requires_review or not self.allow_automatic_ready:
            status = DecisionStatus.REVIEW_REQUIRED
            summary = "The dossier requires human review before it can be resolved."
        else:
            status = DecisionStatus.READY
            summary = "All configured dossier checks passed with sufficient evidence."

        return DossierDecision(
            status=status,
            ruleset_id=self.ruleset_id,
            ruleset_version=self.ruleset_version,
            discrepancies=discrepancies,
            summary=summary,
        )

    def build_report(
        self,
        case_context: DossierCaseContext,
        decision: DossierDecision,
    ) -> dict[str, Any]:
        return {
            "report_version": "1",
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "ruleset_id": decision.ruleset_id,
            "ruleset_version": decision.ruleset_version,
            "case_id": case_context.case_id,
            "client_id": case_context.client_id,
            "external_reference": case_context.external_reference,
            "decision": decision.model_dump(mode="json"),
            "documents": case_context.documents,
        }
