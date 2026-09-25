/**
 * TypeScript interfaces mirroring the Ironclad-OCR backend Pydantic schemas.
 * Single source of truth for all API response shapes in the frontend.
 */

export type JobStatus =
  | "PENDING"
  | "PROCESSING"
  | "WAITING_HUMAN"
  | "COMPLETED"
  | "FAILED"
  | "DELIVERY_FAILED";

export type ReviewMode = "schema_approval" | "audit_review";

export interface ClientConfig {
  clientId: string;
  displayName: string;
  enabledModules: string[];
  defaultRoute: string;
  reviewMode: ReviewMode;
  workflowId: string;
  providerProfile: string;
  rulesetVersion: string;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
}

export interface AuditDiscrepancy {
  type: string;
  item?: string;
  message?: string;
  why?: string;
  where?: {
    document?: string;
    field?: string;
    item_description?: string;
  };
  detected_from?: {
    sources?: string[];
    comparison?: string;
  };
  anomaly?: {
    kind?: string;
    metric?: string;
    expected?: string | number;
    actual?: string | number;
    delta?: number;
    variance_pct?: number;
  };
  invoice_qty?: number;
  po_qty?: number;
  receipt_qty?: number;
  invoice_price?: number;
  po_price?: number;
}

export interface AuditReport {
  status: "CLEARED" | "BLOCKED_DISCREPANCY" | "WAITING_WAREHOUSE" | string;
  discrepancies: AuditDiscrepancy[];
  requires_human?: boolean;
  confidence?: number;
  plugin_id?: string;
  plugin_version?: string;
  audit_trail?: Array<{
    step?: string;
    message?: string;
    evidence?: string[];
    [key: string]: unknown;
  }>;
  shortage_detected?: boolean;
  notification?: {
    shortage_detected: boolean;
    severity?: "success" | "warning" | "info" | string;
    title: string;
    message: string;
    discrepancy_count?: number;
  };
}

export interface FieldDefinition {
  key: string;
  type: "str" | "float" | "date" | "list";
  description: string;
}

export interface ProposedSchema {
  vendor_name: string;
  version: number;
  fields: FieldDefinition[];
}

/** Shape of extracted_data for a COMPLETED job */
export interface ExtractedData {
  [key: string]: unknown;
  line_items?: LineItem[];
  audit_report?: AuditReport;
  processing_notification?: {
    shortage_detected: boolean;
    severity?: "success" | "warning" | "info" | string;
    title: string;
    message: string;
    discrepancy_count?: number;
  };
}

/** Shape of extracted_data for a WAITING_HUMAN job */
export interface WaitingHumanData {
  proposed_schema: ProposedSchema;
  fingerprint_hash: string | null;
  ocr_text_cache: string | null;
}

export interface Job {
  job_id: string;
  client_id: string;
  status: JobStatus;
  file_url: string;
  vendor_detected: string | null;
  extracted_data: ExtractedData | WaitingHumanData | null;
  error_log: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestResponse {
  job_ids: string[];
}

export interface ApprovePayload {
  job_id: string;
  client_id?: string;
  vendor_name: string;
  schema_definition: ProposedSchema;
}

export interface ApproveResponse {
  status: string;
  job_id: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  redis: { ok: boolean; error?: string };
  supabase: { ok: boolean; error?: string; status?: string };
}

export type DossierStatus =
  | "INGESTED"
  | "PROCESSING"
  | "AWAITING_REVIEW"
  | "RESOLVED"
  | "FAILED";

export type DecisionStatus = "READY" | "BLOCKED" | "REVIEW_REQUIRED";

export type DossierDocumentType =
  | "DUM_MLV"
  | "DUA"
  | "BAD"
  | "BILL_OF_LADING"
  | "FREIGHT_INVOICE"
  | "SUPPLIER_DOCUMENT"
  | "UNKNOWN";

export interface DossierFact {
  field_path: string;
  value: string | number | boolean | null;
  page: number;
  source_text: string;
  confidence: number;
  bbox?: number[] | null;
}

export interface DossierDocument {
  document_id: string;
  source_artifact_id: string;
  original_filename: string;
  file_url: string;
  sha256: string;
  page_start: number;
  page_end: number;
  document_type: DossierDocumentType;
  classification_confidence: number;
  provider_id: string;
  model_id: string;
  schema_version: string;
  facts: DossierFact[];
}

export interface DossierSource {
  document_id: string;
  original_filename: string;
  file_url: string;
  sha256: string;
  page_start: number;
  page_end: number;
  status: string;
  issuer_party_id?: string | null;
  provenance_status?: "COMPLETE" | "MISSING_SENDER" | "MISSING_ISSUER" | "MISSING_BOTH";
  intake_channel?: "WEB_UPLOAD" | "API";
  sender_party_name?: string | null;
  issuer_party_name?: string | null;
}

export interface DossierComparedValue {
  document_id: string;
  field_path: string;
  value: string | number | boolean | null;
  evidence: {
    document_id: string;
    field_path: string;
    page: number;
    source_text: string;
    confidence: number;
    bbox?: number[] | null;
  };
}

export interface DossierDiscrepancy {
  rule_id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  values: DossierComparedValue[];
}

export interface DossierDecision {
  decision_id: string;
  decision_version: number;
  status: DecisionStatus;
  ruleset_id: string;
  ruleset_version: string;
  summary: string;
  discrepancies: DossierDiscrepancy[];
  created_at: string;
}

export interface DossierReview {
  review_id: string;
  status: "PENDING" | "RESOLVED" | "CANCELLED";
  resolution: "APPROVED" | "REJECTED" | "OVERRIDDEN" | null;
  comment: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface DossierSummary {
  case_id: string;
  client_id: string;
  external_reference: string | null;
  workflow_id: string;
  workflow_version: string;
  status: DossierStatus;
  decision_status: DecisionStatus | null;
  decision_version: number | null;
  source_count: number;
  created_at: string;
  updated_at: string;
}

export interface DossierDetail {
  case: DossierSummary;
  sources: DossierSource[];
  documents: DossierDocument[];
  decision: DossierDecision | null;
  reviews: DossierReview[];
  audit_events: Array<{
    event_id: string;
    event_type: string;
    event_data: Record<string, unknown>;
    created_at: string;
  }>;
}

export interface DossierIngestResponse {
  case_id: string;
  document_ids: string[];
  job_ids: string[];
  status: DossierStatus;
}

export type PartyScope = "INTERNAL" | "EXTERNAL";

export interface SourceParty {
  party_id: string;
  client_id: string;
  name: string;
  scope: PartyScope;
  party_type: string;
  is_active: boolean;
}

export interface NotificationItem {
  notification_id: string;
  case_id: string | null;
  notification_type: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  read_at: string | null;
  created_at: string;
}

export interface RuleDefinition {
  rule_id?: string;
  template_type: "REQUIRED_DOCUMENT" | "FIELD_REQUIRED" | "EXACT_MATCH" | "NUMERIC_TOLERANCE" | "DATE_WINDOW" | "AUTHORITY_PRECEDENCE";
  name: string;
  field_path?: string | null;
  parameters?: Record<string, unknown>;
  severity?: "info" | "warning" | "critical";
  failure_outcome?: "BLOCKED" | "REVIEW_REQUIRED";
  is_active?: boolean;
}

export interface RuleSet {
  ruleset_id: string;
  client_id: string;
  workflow_id: string;
  version: number;
  status: "DRAFT" | "ACTIVE" | "RETIRED";
  name: string;
  confirmation_comment: string | null;
  rules: RuleDefinition[];
}
