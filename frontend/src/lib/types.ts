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
