/**
 * Centralised API client for the Ironclad-OCR backend.
 * All network calls go through here — never call fetch() directly in components.
 */
import type {
  ApprovePayload,
  ApproveResponse,
  DossierDetail,
  DossierIngestResponse,
  DossierSummary,
  HealthResponse,
  IngestResponse,
  Job,
  NotificationItem,
  RuleDefinition,
  RuleSet,
  SourceParty,
} from "./types";
import { DEFAULT_CLIENT_ID } from "./clients";
import { getSupabaseClient } from "./supabase";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const session = await getSupabaseClient()?.auth.getSession();
  const accessToken = session?.data.session?.access_token;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore JSON parse errors from error bodies
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

export async function ingestDocument(
  file: File,
  clientId: string = DEFAULT_CLIENT_ID,
): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("client_id", clientId);
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: form,
  });
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export async function listJobs(params?: {
  status?: string;
  clientId?: string;
  limit?: number;
  offset?: number;
}): Promise<Job[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.clientId) qs.set("client_id", params.clientId);
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request<Job[]>(`/jobs${query}`);
}

export async function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/jobs/${jobId}`);
}

// ---------------------------------------------------------------------------
// File streaming
// ---------------------------------------------------------------------------

/** 
 * Returns the URL to view a job's document.
 * Now reads the file_url directly from the job record (Supabase Storage public URL).
 */
export function getFileUrl(job: Job): string {
  return job.file_url;
}

// ---------------------------------------------------------------------------
// Schema approval
// ---------------------------------------------------------------------------

export async function approveSchema(
  payload: ApprovePayload,
): Promise<ApproveResponse> {
  return request<ApproveResponse>("/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function ingestDossier(
  files: File[],
  clientId: string,
  externalReference?: string,
  provenance?: {
    senderPartyId?: string;
    issuerPartyIds?: Record<string, string | undefined>;
    channelReference?: string;
  },
): Promise<DossierIngestResponse> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  form.append("client_id", clientId);
  if (externalReference?.trim()) {
    form.append("external_reference", externalReference.trim());
  }
  form.append("intake_channel", "WEB_UPLOAD");
  if (provenance?.senderPartyId) form.append("sender_party_id", provenance.senderPartyId);
  if (provenance?.channelReference?.trim()) form.append("channel_reference", provenance.channelReference.trim());
  if (provenance?.issuerPartyIds) {
    form.append("issuer_manifest_json", JSON.stringify(provenance.issuerPartyIds));
  }
  return request<DossierIngestResponse>("/dossiers", {
    method: "POST",
    body: form,
  });
}

export async function listParties(clientId: string, activeOnly = true): Promise<SourceParty[]> {
  const query = new URLSearchParams({ client_id: clientId, active_only: String(activeOnly) });
  return request<SourceParty[]>(`/admin/parties?${query.toString()}`);
}

export async function createParty(clientId: string, payload: Omit<SourceParty, "party_id" | "client_id">): Promise<SourceParty> {
  const query = new URLSearchParams({ client_id: clientId });
  return request<SourceParty>(`/admin/parties?${query.toString()}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

export async function listRuleSets(clientId: string): Promise<RuleSet[]> {
  return request<RuleSet[]>(`/admin/rule-sets?${new URLSearchParams({ client_id: clientId })}`);
}

export async function createRuleSet(clientId: string, payload: { name: string; rules: RuleDefinition[] }): Promise<RuleSet> {
  return request<RuleSet>(`/admin/rule-sets?${new URLSearchParams({ client_id: clientId })}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

export async function activateRuleSet(rulesetId: string, clientId: string, confirmationComment: string): Promise<RuleSet> {
  return request<RuleSet>(`/admin/rule-sets/${rulesetId}/activate`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, confirmation_comment: confirmationComment }),
  });
}

export async function listNotifications(clientId: string, unreadOnly = false): Promise<NotificationItem[]> {
  const query = new URLSearchParams({ client_id: clientId, unread_only: String(unreadOnly) });
  return request<NotificationItem[]>(`/admin/notifications?${query.toString()}`);
}

export async function markNotificationRead(notificationId: string, clientId: string): Promise<NotificationItem> {
  return request<NotificationItem>(`/admin/notifications/${notificationId}/read?${new URLSearchParams({ client_id: clientId })}`, { method: "POST" });
}

export async function listDossiers(params: {
  clientId: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<DossierSummary[]> {
  const query = new URLSearchParams({ client_id: params.clientId });
  if (params.status) query.set("status", params.status);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  return request<DossierSummary[]>(`/dossiers?${query.toString()}`);
}

export async function getDossier(
  caseId: string,
  clientId: string,
): Promise<DossierDetail> {
  const query = new URLSearchParams({ client_id: clientId });
  return request<DossierDetail>(`/dossiers/${caseId}?${query.toString()}`);
}

export async function reviewDossier(
  caseId: string,
  payload: {
    client_id: string;
    action: "APPROVE" | "REJECT" | "OVERRIDE";
    comment: string;
    expected_decision_version: number;
    idempotency_key: string;
  },
): Promise<{ case_id: string; status: string; review: unknown }> {
  return request(`/dossiers/${caseId}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function reprocessDossier(
  caseId: string,
  payload: {
    client_id: string;
    document_ids: string[];
    reason: string;
  },
): Promise<{ case_id: string; job_ids: string[]; status: string }> {
  return request(`/dossiers/${caseId}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getDossierReportUrl(
  caseId: string,
  clientId: string,
  format: "json" | "pdf",
): string {
  const query = new URLSearchParams({ client_id: clientId, format });
  return `${BASE_URL}/dossiers/${caseId}/report?${query.toString()}`;
}

export async function downloadDossierReport(
  caseId: string,
  clientId: string,
  format: "json" | "pdf",
): Promise<void> {
  const session = await getSupabaseClient()?.auth.getSession();
  const token = session?.data.session?.access_token;
  const response = await fetch(getDossierReportUrl(caseId, clientId, format), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new ApiError(response.status, `Report download failed (${response.status})`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `ironclad-${caseId}.${format === "pdf" ? "pdf" : "json"}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
