/**
 * Centralised API client for the Ironclad-OCR backend.
 * All network calls go through here — never call fetch() directly in components.
 */
import type {
  ApprovePayload,
  ApproveResponse,
  HealthResponse,
  IngestResponse,
  Job,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
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
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
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

export async function ingestDocument(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
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
  limit?: number;
  offset?: number;
}): Promise<Job[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
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
