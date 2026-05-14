"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircleIcon,
  CpuIcon,
  DotsThreeIcon,
  FilePdfIcon,
  ShieldWarningIcon,
  SpinnerGapIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import { UploadIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useIngest } from "@/hooks/use-ingest";
import { useJobs } from "@/hooks/use-jobs";
import type { Job, JobStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Status configuration
// ---------------------------------------------------------------------------
const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; icon: React.ElementType; className: string }
> = {
  PENDING: {
    label: "PENDING",
    icon: SpinnerGapIcon,
    className: "bg-zinc-900/50 text-zinc-400 border-zinc-700/50",
  },
  PROCESSING: {
    label: "PROCESSING",
    icon: CpuIcon,
    className: "bg-blue-950/40 text-blue-300 border-blue-900/60",
  },
  WAITING_HUMAN: {
    label: "AWAITING REVIEW",
    icon: DotsThreeIcon,
    className: "bg-amber-950/30 text-amber-300 border-amber-900/50",
  },
  COMPLETED: {
    label: "CLEARED",
    icon: CheckCircleIcon,
    className: "bg-emerald-950/30 text-emerald-300 border-emerald-900/50",
  },
  FAILED: {
    label: "FAILED",
    icon: XCircleIcon,
    className: "bg-red-950/40 text-red-300 border-red-900/60",
  },
  DELIVERY_FAILED: {
    label: "DELIVERY FAILED",
    icon: ShieldWarningIcon,
    className: "bg-red-950/40 text-red-300 border-red-900/60",
  },
};

function StatusBadge({ status }: { status: JobStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.FAILED;
  const Icon = cfg.icon;
  const isSpinning = status === "PROCESSING" || status === "PENDING";

  return (
    <Badge
      variant="outline"
      className={`rounded-md border px-2 py-1 text-[11px] font-medium tracking-wide ${cfg.className}`}
    >
      <Icon
        className={`h-3.5 w-3.5 ${isSpinning ? "animate-spin" : ""}`}
        weight="fill"
      />
      <span className="font-mono">{cfg.label}</span>
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Ingest panel
// ---------------------------------------------------------------------------
interface IngestPanelProps {
  onSuccess: () => void;
}

function IngestPanel({ onSuccess }: IngestPanelProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const { ingest, isUploading, error, result, reset } = useIngest();

  const clearDialogState = React.useCallback(() => {
    setSelectedFile(null);
    setIsDragging(false);
    reset();
  }, [reset]);

  // Refresh the live table after the API returns queued jobs.
  React.useEffect(() => {
    if (result) {
      const t = setTimeout(() => {
        onSuccess();
      }, 1200);
      return () => clearTimeout(t);
    }
  }, [result, onSuccess]);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) return;
    await ingest(selectedFile);
  }

  return (
    <section
      id="ingestion"
      className="mb-6 rounded-xl border border-zinc-800 bg-zinc-950/40 p-4 ring-1 ring-zinc-800/40"
    >
      <div className="mb-4 flex flex-col gap-1">
        <h2 className="text-sm font-semibold tracking-tight text-zinc-100">
          Document Ingestion
        </h2>
        <p className="text-xs leading-5 text-zinc-500">
          Upload a PDF and route it through splitting, schema lookup, extraction, matching, and delivery.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div>
          <div
            role="button"
            tabIndex={0}
            aria-label="Drop PDF here or click to browse"
            className={`flex min-h-44 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-zinc-900/50 px-6 py-6 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 ${
              isDragging
                ? "border-emerald-500/50 bg-emerald-950/10"
                : selectedFile
                  ? "border-zinc-600 bg-zinc-900/30"
                  : "border-zinc-700 hover:border-zinc-600"
            }`}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="sr-only"
              onChange={handleFileChange}
            />

            {selectedFile ? (
              <>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-900/60 bg-emerald-950/30">
                  <FilePdfIcon className="h-5 w-5 text-emerald-400" weight="fill" />
                </div>
                <div className="text-sm font-medium text-zinc-200">{selectedFile.name}</div>
                <div className="text-xs text-zinc-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB · Click to change
                </div>
              </>
            ) : (
              <>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-950/60">
                  <UploadIcon className="h-5 w-5 text-zinc-300" />
                </div>
                <div className="text-sm font-medium text-zinc-200">
                  Drag &amp; drop PDF here
                </div>
                <div className="text-xs text-zinc-500">
                  Supports Invoices, Bills of Lading, POs, and Customs Declarations
                </div>
              </>
            )}
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-900/50 bg-red-950/20 px-3 py-2 text-xs text-red-300">
              <XCircleIcon className="mt-0.5 h-4 w-4 shrink-0" weight="fill" />
              {error}
            </div>
          )}
          {result && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-900/50 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-300">
              <CheckCircleIcon className="mt-0.5 h-4 w-4 shrink-0" weight="fill" />
              {result.job_ids.length} job{result.job_ids.length !== 1 ? "s" : ""} queued
              successfully. Pipeline is processing.
            </div>
          )}
        </div>

        <div className="flex flex-col justify-between gap-4 rounded-lg border border-zinc-800 bg-zinc-900/25 p-4">
          <div className="flex flex-col gap-2">
            <div className="text-sm font-medium text-zinc-100">Demo path</div>
            <p className="text-xs leading-5 text-zinc-500">
              Use an invoice PDF to demonstrate schema discovery, human approval for new layouts,
              and 3-way matching against ERP evidence.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              className="text-zinc-300 hover:bg-zinc-900/60"
              onClick={clearDialogState}
              disabled={isUploading}
            >
              Reset
            </Button>
            <Button
              className="border border-emerald-500/20 bg-zinc-100 text-zinc-950 shadow-[0_0_0_1px_rgba(16,185,129,0.12),0_0_24px_rgba(16,185,129,0.10)] hover:bg-zinc-200 disabled:opacity-50"
              onClick={handleUpload}
              disabled={!selectedFile || isUploading || !!result}
            >
              {isUploading ? (
                <>
                  <SpinnerGapIcon className="h-4 w-4 animate-spin" />
                  <span>Uploading…</span>
                </>
              ) : (
                "Upload & Process"
              )}
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

function deriveDocumentType(job: Job): string {
  if (!job.vendor_detected && job.status === "WAITING_HUMAN") return "UNKNOWN";
  return "INVOICE";
}

function isBlockedByAudit(job: Job): boolean {
  const data = job.extracted_data;
  if (!data || typeof data !== "object" || !("audit_report" in data)) return false;
  const status = data.audit_report?.status ?? "";
  return status === "BLOCKED_DISCREPANCY" || status === "WAITING_WAREHOUSE";
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const router = useRouter();
  const { jobs, isLoading, error, refetch } = useJobs({ pollInterval: 5000 });

  // Derived stats
  const totalJobs = jobs.length;
  const completedJobs = jobs.filter((j) => j.status === "COMPLETED").length;
  const stpRate =
    totalJobs > 0 ? ((completedJobs / totalJobs) * 100).toFixed(1) : "—";
  const pendingCount = jobs.filter((j) =>
    ["PENDING", "PROCESSING"].includes(j.status),
  ).length;
  const blockedCount = jobs.filter(isBlockedByAudit).length;

  return (
    <div className="min-h-screen w-full bg-zinc-950 text-zinc-100">
      {/* Background decoration */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-32 left-1/2 h-[560px] w-[900px] -translate-x-1/2 rounded-full bg-gradient-to-b from-zinc-800/20 to-transparent blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.05)_1px,transparent_0)] [background-size:22px_22px] opacity-60" />
      </div>

      <div className="relative mx-auto w-full max-w-7xl px-6 py-8">
        {/* Header */}
        <header className="mb-8 flex flex-col gap-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SidebarTrigger className="-ml-2 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-100" />
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/40">
                <div className="h-4 w-4 rounded-sm bg-gradient-to-br from-zinc-100 to-zinc-400" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-xl font-semibold tracking-tight">
                  Ironclad IDP Command Center
                </h1>
                <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                  <span className="font-mono tracking-wider">IRONCLAD OS</span>
                  <span className="text-zinc-700">/</span>
                  <span className="font-mono">DECISION PIPELINE</span>
                </div>
              </div>
            </div>

            <div className="hidden items-center gap-3 sm:flex">
              <div className="flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900/30 px-3 py-2">
                <CpuIcon className="h-4 w-4 text-zinc-400" weight="fill" />
                <span className="text-xs text-zinc-400">Queue</span>
                <Separator orientation="vertical" className="mx-1 h-4 bg-zinc-800" />
                <span className="font-mono text-xs tabular-nums text-zinc-200">
                  {isLoading ? "—" : `${pendingCount} inflight`}
                </span>
              </div>
              <a
                id="ingest-document-btn"
                href="#ingestion"
                className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-emerald-500/30 bg-zinc-100 px-3 text-sm font-medium text-zinc-950 shadow-[0_0_0_1px_rgba(16,185,129,0.15),0_0_24px_rgba(16,185,129,0.12)] transition-colors hover:bg-zinc-200 hover:shadow-[0_0_0_1px_rgba(16,185,129,0.22),0_0_30px_rgba(16,185,129,0.16)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              >
                <span className="font-mono text-sm">+</span>
                <span className="text-sm font-medium">Ingest Document</span>
              </a>
            </div>
          </div>

          {/* Stats cards */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="bg-zinc-950/40 ring-1 ring-zinc-800/70">
              <CardHeader className="pb-0">
                <CardTitle className="text-sm text-zinc-300">Volume (Total)</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between gap-6">
                <div className="flex flex-col gap-1">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-100">
                    {isLoading ? "—" : totalJobs}{" "}
                    <span className="text-sm font-medium text-zinc-400">Jobs</span>
                  </div>
                  <div className="text-xs text-zinc-500">All-time ingested documents</div>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/40">
                  <FilePdfIcon className="h-5 w-5 text-zinc-300" weight="fill" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-950/40 ring-1 ring-zinc-800/70">
              <CardHeader className="pb-0">
                <CardTitle className="text-sm text-zinc-300">STP Rate (Auto-Processed)</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between gap-6">
                <div className="flex flex-col gap-1">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-100">
                    {isLoading ? "—" : `${stpRate}%`}
                  </div>
                  <div className="text-xs text-zinc-500">Completed without human intervention</div>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/40">
                  <CpuIcon className="h-5 w-5 text-zinc-300" weight="fill" />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-zinc-950/40 ring-1 ring-zinc-800/70">
              <CardHeader className="pb-0">
                <CardTitle className="text-sm text-zinc-300">Review Queue</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between gap-6">
                <div className="flex flex-col gap-1">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-100">
                    {isLoading
                      ? "—"
                      : jobs.filter((j) => j.status === "WAITING_HUMAN").length + blockedCount}{" "}
                    <span className="text-sm font-medium text-amber-300">Jobs</span>
                  </div>
                  <div className="text-xs text-zinc-500">Schema approvals and audit-blocked documents</div>
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-amber-900/60 bg-amber-950/30">
                  <ShieldWarningIcon className="h-5 w-5 text-amber-300" weight="fill" />
                </div>
              </CardContent>
            </Card>
          </div>
        </header>

        <IngestPanel onSuccess={refetch} />

        {/* Live Pipeline Table */}
        <section className="rounded-xl border border-zinc-800 bg-zinc-950/40 ring-1 ring-zinc-800/40">
          <div className="flex items-center justify-between px-4 py-4">
            <div className="flex flex-col">
              <h2 className="text-sm font-semibold tracking-tight text-zinc-100">
                Live Processing Pipeline
              </h2>
              <p className="text-xs text-zinc-500">
                Real-time view of document ingestion, validation, and downstream sync.
              </p>
            </div>
            <div className="hidden items-center gap-2 md:flex">
              <Badge
                variant="outline"
                className="rounded-md border border-zinc-800 bg-zinc-900/30 px-2 py-1 text-[11px] text-zinc-300"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-mono">LIVE · {totalJobs} records</span>
              </Badge>
            </div>
          </div>

          <Separator className="bg-zinc-800" />

          {/* Loading skeleton */}
          {isLoading && (
            <div className="flex items-center justify-center py-16 text-zinc-500">
              <SpinnerGapIcon className="mr-2 h-5 w-5 animate-spin" />
              <span className="text-sm">Loading pipeline…</span>
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
              <XCircleIcon className="h-8 w-8 text-red-400" weight="fill" />
              <p className="text-sm text-red-300">{error}</p>
              <p className="text-xs text-zinc-500">
                Make sure the Ironclad-OCR backend is running on port 8000.
              </p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && jobs.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/40">
                <FilePdfIcon className="h-6 w-6 text-zinc-600" weight="light" />
              </div>
              <p className="text-sm font-medium text-zinc-400">No documents ingested yet</p>
              <p className="text-xs text-zinc-600">
                Click &quot;Ingest Document&quot; to upload your first PDF.
              </p>
            </div>
          )}

          {/* Data table */}
          {!isLoading && !error && jobs.length > 0 && (
            <div className="overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-transparent">
                    {["ID", "Document Type", "Vendor", "Time", "Status"].map((h) => (
                      <TableHead
                        key={h}
                        className="h-11 border-b border-zinc-800 bg-zinc-900/30 px-4 text-xs font-medium uppercase tracking-wider text-zinc-500"
                      >
                        {h}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow
                      key={job.job_id}
                      id={`job-row-${job.job_id}`}
                      onClick={() => router.push(`/validation/${job.job_id}`)}
                      className="cursor-pointer border-zinc-800/60 transition-colors hover:bg-zinc-900/25"
                    >
                      <TableCell className="px-4 py-3 font-mono text-xs text-zinc-400">
                        {job.job_id.split("-")[0].toUpperCase()}
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <span className="inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/30 px-2 py-1 text-xs font-medium text-zinc-200">
                          {deriveDocumentType(job)}
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-zinc-100">
                        {job.vendor_detected ?? (
                          <span className="text-zinc-600 italic">Unidentified</span>
                        )}
                      </TableCell>
                      <TableCell className="px-4 py-3 font-mono text-sm tabular-nums text-zinc-400">
                        {formatRelativeTime(job.created_at)}
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <StatusBadge status={job.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
