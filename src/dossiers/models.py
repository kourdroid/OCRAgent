from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class CaseStatus(StrEnum):
    INGESTED = "INGESTED"
    PROCESSING = "PROCESSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class DecisionStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ReviewResolution(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


class PartyScope(StrEnum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class IntakeChannel(StrEnum):
    WEB_UPLOAD = "WEB_UPLOAD"
    API = "API"


class ProvenanceStatus(StrEnum):
    COMPLETE = "COMPLETE"
    MISSING_SENDER = "MISSING_SENDER"
    MISSING_ISSUER = "MISSING_ISSUER"
    MISSING_BOTH = "MISSING_BOTH"


class RuleSetStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class RuleTemplateType(StrEnum):
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    FIELD_REQUIRED = "FIELD_REQUIRED"
    EXACT_MATCH = "EXACT_MATCH"
    NUMERIC_TOLERANCE = "NUMERIC_TOLERANCE"
    DATE_WINDOW = "DATE_WINDOW"
    AUTHORITY_PRECEDENCE = "AUTHORITY_PRECEDENCE"


class DocumentType(StrEnum):
    DUM_MLV = "DUM_MLV"
    DUA = "DUA"
    BAD = "BAD"
    BILL_OF_LADING = "BILL_OF_LADING"
    FREIGHT_INVOICE = "FREIGHT_INVOICE"
    SUPPLIER_DOCUMENT = "SUPPLIER_DOCUMENT"
    UNKNOWN = "UNKNOWN"


CANONICAL_FACT_PATHS = Literal[
    "dossier_reference",
    "declaration_number",
    "bill_of_lading_number",
    "container_number",
    "voyage_number",
    "vessel_name",
    "importer_name",
    "exporter_name",
    "carrier_name",
    "declarant_name",
    "country_of_origin",
    "port_of_loading",
    "port_of_discharge",
    "declaration_date",
    "shipping_date",
    "arrival_date",
    "release_date",
    "package_count",
    "gross_weight",
    "net_weight",
    "quantity",
    "goods_value",
    "freight_amount",
    "currency",
]


class DocumentSegment(BaseModel):
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_range(self) -> "DocumentSegment":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class DocumentClassification(BaseModel):
    segments: list[DocumentSegment] = Field(min_length=1)


class ExtractedFact(BaseModel):
    field_path: CANONICAL_FACT_PATHS
    value: str | int | float | bool | None
    page: int = Field(ge=1)
    source_text: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_bbox(self) -> "ExtractedFact":
        if self.bbox is not None and any(value < 0.0 or value > 1.0 for value in self.bbox):
            raise ValueError("bbox coordinates must be normalized between 0 and 1")
        return self


class DocumentExtraction(BaseModel):
    document_type: DocumentType
    facts: list[ExtractedFact] = Field(default_factory=list)


class EvidenceReference(BaseModel):
    document_id: str
    field_path: str
    page: int
    source_text: str
    confidence: float
    bbox: list[float] | None = None


class ComparedValue(BaseModel):
    document_id: str
    field_path: str
    value: str | int | float | bool | None
    evidence: EvidenceReference


class DossierDiscrepancy(BaseModel):
    rule_id: str
    severity: Literal["info", "warning", "critical"]
    message: str
    values: list[ComparedValue] = Field(default_factory=list)


class DossierDecision(BaseModel):
    status: DecisionStatus
    ruleset_id: str
    ruleset_version: str
    discrepancies: list[DossierDiscrepancy] = Field(default_factory=list)
    summary: str


class DossierCaseContext(BaseModel):
    case_id: str
    client_id: str
    external_reference: str | None = None
    documents: list[dict[str, Any]] = Field(default_factory=list)


class DossierReviewRequest(BaseModel):
    client_id: str = Field(min_length=1)
    action: Literal["APPROVE", "REJECT", "OVERRIDE"]
    comment: str = Field(min_length=3, max_length=2000)
    expected_decision_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


class DossierReprocessRequest(BaseModel):
    client_id: str = Field(min_length=1)
    document_ids: list[str] = Field(min_length=1)
    reason: str = Field(min_length=3, max_length=2000)


class PartyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    scope: PartyScope
    party_type: str = Field(min_length=2, max_length=64)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_party_type(self) -> "PartyCreateRequest":
        allowed = {
            PartyScope.EXTERNAL: {"INSTITUTION", "SERVICE_PROVIDER", "CLIENT", "SUPPLIER", "OTHER"},
            PartyScope.INTERNAL: {"DIRECTION", "FINANCE", "COMMERCIAL", "OTHER"},
        }
        if self.party_type not in allowed[self.scope]:
            raise ValueError("party_type is not valid for the selected scope")
        return self


class PartyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    scope: PartyScope | None = None
    party_type: str | None = Field(default=None, min_length=2, max_length=64)
    is_active: bool | None = None


class RuleDefinitionRequest(BaseModel):
    rule_id: str | None = Field(default=None, min_length=3, max_length=200)
    template_type: RuleTemplateType
    name: str = Field(min_length=3, max_length=200)
    field_path: str | None = Field(default=None, max_length=128)
    authoritative_document_type: DocumentType | None = None
    compared_document_type: DocumentType | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    severity: Literal["info", "warning", "critical"] = "warning"
    failure_outcome: Literal["BLOCKED", "REVIEW_REQUIRED"] = "REVIEW_REQUIRED"
    is_active: bool = True


class RuleSetCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    ruleset_id: str | None = Field(default=None, min_length=3, max_length=200)
    rules: list[RuleDefinitionRequest] = Field(default_factory=list)


class RuleSetActivationRequest(BaseModel):
    client_id: str = Field(min_length=1)
    confirmation_comment: str = Field(min_length=8, max_length=2000)


class DossierReport(BaseModel):
    report_version: str = "1"
    case: dict[str, Any]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]]
    decision: dict[str, Any]
    reviews: list[dict[str, Any]]
    audit_events: list[dict[str, Any]]
