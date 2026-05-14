"use client";

import * as React from "react";
import { use } from "react";
import Link from "next/link";
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  CpuIcon,
  FilePdfIcon,
  ShieldWarningIcon,
  SpinnerGapIcon,
  XCircleIcon,
  WarningOctagonIcon,
  TableIcon,
  FileTextIcon,
  CalendarBlankIcon,
  BuildingsIcon,
  CaretLeftIcon,
  CaretRightIcon,
  ArrowsOutIcon,
} from "@phosphor-icons/react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar";

import { approveSchema, getFileUrl } from "@/lib/api";
import { useJob } from "@/hooks/use-job";
import type { AuditDiscrepancy, ExtractedData, Job, LineItem, WaitingHumanData } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function isWaitingHumanData(data: unknown): data is WaitingHumanData {
  return (
    typeof data === "object" &&
    data !== null &&
    "proposed_schema" in data &&
    typeof (data as Record<string, unknown>).proposed_schema === "object"
  );
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "string") return val;
  if (typeof val === "number") return String(val);
  if (typeof val === "boolean") return val ? "Yes" : "No";
  return JSON.stringify(val);
}

function formatAuditValue(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  if (typeof val === "number") return Number.isInteger(val) ? String(val) : val.toFixed(2);
  return String(val);
}

// Top-level keys to render as metadata (exclude arrays and nested objects)
const METADATA_KEYS_PRIORITY = [
  "vendor_name",
  "invoice_number",
  "date",
  "currency",
  "po_number",
  "order_reference",
];

// ---------------------------------------------------------------------------
// PDF Viewer (iframe-based — no extra npm packages needed)
// ---------------------------------------------------------------------------
interface PdfViewerProps {
  job: Job;
}

function PdfViewer({ job }: PdfViewerProps) {
  const src = getFileUrl(job);
  const [error, setError] = React.useState(false);

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex h-12 flex-none items-center gap-2 border-b border-zinc-800/50 bg-zinc-900/30 px-4">
        <FilePdfIcon className="h-4 w-4 text-zinc-500" />
        <span className="font-mono text-xs text-zinc-500 truncate">
          {job.job_id}.pdf
        </span>
        <div className="ml-auto flex items-center gap-1">
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            title="Open in new tab"
            className="inline-flex h-7 w-7 items-center justify-center rounded text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          >
            <ArrowsOutIcon className="h-4 w-4" />
          </a>
        </div>
      </div>

      {/* PDF frame */}
      <div className="relative flex-1 bg-zinc-900/80">
        {error ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center px-8">
            <FilePdfIcon className="h-16 w-16 text-zinc-700" weight="light" />
            <p className="text-sm text-zinc-500">
              Could not load PDF preview. The backend may not be running or the file may not yet be on disk.
            </p>
            <a
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-emerald-500 hover:underline"
            >
              Try opening directly →
            </a>
          </div>
        ) : (
          <iframe
            src={src}
            title="Invoice PDF"
            className="h-full w-full border-0"
            onError={() => setError(true)}
          />
        )}
        {/* Subtle crosshatch overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(45deg,#000 25%,transparent 25%,transparent 75%,#000 75%,#000),repeating-linear-gradient(45deg,#000 25%,#fff 25%,#fff 75%,#000 75%,#000)",
            backgroundPosition: "0 0,10px 10px",
            backgroundSize: "20px 20px",
          }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Right panel: Extraction content per status
// ---------------------------------------------------------------------------
function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 py-2">
      <div className="h-4 w-24 rounded bg-zinc-800 animate-pulse" />
      <div className="h-4 flex-1 rounded bg-zinc-800/60 animate-pulse" />
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="space-y-6 p-8">
      <div className="space-y-2">
        <div className="h-6 w-48 rounded bg-zinc-800 animate-pulse" />
        <div className="h-4 w-80 rounded bg-zinc-800/50 animate-pulse" />
      </div>
      <Card className="border-zinc-800 bg-zinc-900/30">
        <CardContent className="pt-6 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
        </CardContent>
      </Card>
    </div>
  );
}

interface CompletedPanelProps {
  data: ExtractedData;
}

function CompletedPanel({ data }: CompletedPanelProps) {
  // Collect metadata fields — prioritised keys first, then the rest
  const allKeys = Object.keys(data).filter(
    (k) => k !== "line_items" && k !== "audit_report" && !Array.isArray(data[k]) && typeof data[k] !== "object",
  );
  const orderedKeys = [
    ...METADATA_KEYS_PRIORITY.filter((k) => allKeys.includes(k)),
    ...allKeys.filter((k) => !METADATA_KEYS_PRIORITY.includes(k)),
  ];

  const lineItems = data.line_items as LineItem[] | undefined;
  const audit = data.audit_report;
  const processingNotification = data.processing_notification;

  const isBlocked = audit?.status === "BLOCKED_DISCREPANCY";

  return (
    <div className="space-y-8 p-8">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Extraction Report
        </h2>
        <p className="mt-1 text-sm text-zinc-400">
          AI extraction completed. Data validated against schema.
        </p>
      </div>

      {/* Audit status banner */}
      {audit && (
        <Card
          className={`shadow-none ${
            isBlocked
              ? "border-red-900/50 bg-red-950/20 ring-1 ring-inset ring-red-900/50"
              : "border-emerald-900/50 bg-emerald-950/20 ring-1 ring-inset ring-emerald-900/50"
          }`}
        >
          <CardContent className="flex items-start gap-4 p-5">
            {isBlocked ? (
              <WarningOctagonIcon className="mt-0.5 h-6 w-6 shrink-0 text-red-500" weight="fill" />
            ) : (
              <CheckCircleIcon className="mt-0.5 h-6 w-6 shrink-0 text-emerald-500" weight="fill" />
            )}
            <div className="flex flex-col gap-1">
              <h4 className={`text-sm font-semibold uppercase tracking-wide ${isBlocked ? "text-red-400" : "text-emerald-400"}`}>
                {isBlocked ? "Discrepancy Detected" : "Reconciliation Passed"}
              </h4>
              {processingNotification && (
                <p className={`text-sm ${isBlocked ? "text-red-200/90" : "text-emerald-200/90"}`}>
                  {processingNotification.title}: {processingNotification.message}
                </p>
              )}
              {isBlocked && audit.discrepancies?.length > 0 && (
                <div className="mt-3 grid gap-3">
                  {audit.discrepancies.map((d, i) => (
                    <DiscrepancyCard key={i} discrepancy={d} />
                  ))}
                </div>
              )}
              {!isBlocked && (
                <p className="text-sm text-emerald-200/90">
                  All line items reconciled against ERP records.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card className="border-zinc-800 bg-zinc-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500">
            <FileTextIcon className="h-4 w-4" />
            Extracted Metadata
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {orderedKeys.map((key) => (
              <div key={key} className="flex flex-col gap-0.5">
                <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-sm text-zinc-200 break-all">
                  {formatValue(data[key])}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Line Items */}
      {lineItems && lineItems.length > 0 && (
        <div className="space-y-3">
          <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500">
            <TableIcon className="h-4 w-4" />
            Line Items
            <Badge
              variant="outline"
              className="ml-1 rounded-full border-zinc-800 bg-zinc-900 px-2 py-0 text-[10px] text-zinc-400"
            >
              {lineItems.length}
            </Badge>
          </h3>
          <div className="overflow-hidden rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="h-10 px-4 text-left text-xs font-medium text-zinc-500">Description</th>
                  <th className="h-10 px-4 text-right text-xs font-medium text-zinc-500">Qty</th>
                  <th className="h-10 px-4 text-right text-xs font-medium text-zinc-500">Unit Price</th>
                  <th className="h-10 px-4 text-right text-xs font-medium text-zinc-500">Total</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-zinc-800/50 bg-zinc-950 transition-colors hover:bg-zinc-900/50 last:border-0"
                  >
                    <td className="p-4 text-zinc-300">{item.description}</td>
                    <td className="p-4 text-right font-mono tabular-nums text-zinc-400">{item.quantity}</td>
                    <td className="p-4 text-right font-mono tabular-nums text-zinc-400">
                      {typeof item.unit_price === "number" ? item.unit_price.toFixed(2) : item.unit_price}
                    </td>
                    <td className="p-4 text-right font-mono tabular-nums text-zinc-100">
                      {typeof item.total_amount === "number" ? item.total_amount.toFixed(2) : item.total_amount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

interface DiscrepancyCardProps {
  discrepancy: AuditDiscrepancy;
}

function DiscrepancyCard({ discrepancy }: DiscrepancyCardProps) {
  return (
    <div className="rounded-lg border border-red-900/40 bg-zinc-950/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge
          variant="outline"
          className="rounded-md border-red-900/50 bg-red-950/40 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-red-300"
        >
          {discrepancy.type}
        </Badge>
        {discrepancy.item && (
          <span className="font-mono text-xs text-zinc-400">{discrepancy.item}</span>
        )}
      </div>

      <div className="mt-3 space-y-2">
        <p className="text-sm text-red-100">{discrepancy.message ?? discrepancy.type}</p>
        {discrepancy.why && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Why</div>
            <div className="text-sm text-zinc-300">{discrepancy.why}</div>
          </div>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Where</div>
          <div className="mt-2 space-y-1 text-sm text-zinc-300">
            <div>Document: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.where?.document)}</span></div>
            <div>Field: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.where?.field)}</span></div>
            <div>Item: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.where?.item_description ?? discrepancy.item)}</span></div>
          </div>
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Detected From</div>
          <div className="mt-2 space-y-1 text-sm text-zinc-300">
            <div>Sources:</div>
            <div className="font-mono text-xs leading-5 text-zinc-200">
              {(discrepancy.detected_from?.sources ?? []).length > 0
                ? discrepancy.detected_from?.sources?.join(" vs ")
                : "—"}
            </div>
            <div>Check: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.detected_from?.comparison)}</span></div>
          </div>
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Anomaly</div>
          <div className="mt-2 space-y-1 text-sm text-zinc-300">
            <div>Kind: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.anomaly?.kind)}</span></div>
            <div>Metric: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.anomaly?.metric)}</span></div>
            <div>Expected: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.anomaly?.expected)}</span></div>
            <div>Actual: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.anomaly?.actual)}</span></div>
            <div>Delta: <span className="font-mono text-zinc-200">{formatAuditValue(discrepancy.anomaly?.delta)}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface WaitingHumanPanelProps {
  jobId: string;
  data: WaitingHumanData;
  onApproved: () => void;
}

function WaitingHumanPanel({ jobId, data, onApproved }: WaitingHumanPanelProps) {
  const [isApproving, setIsApproving] = React.useState(false);
  const [approveError, setApproveError] = React.useState<string | null>(null);

  async function handleApprove() {
    setIsApproving(true);
    setApproveError(null);
    try {
      await approveSchema({
        job_id: jobId,
        vendor_name: data.proposed_schema.vendor_name,
        schema_definition: data.proposed_schema,
      });
      onApproved();
    } catch (err) {
      setApproveError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setIsApproving(false);
    }
  }

  return (
    <div className="space-y-6 p-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Schema Discovery
        </h2>
        <p className="mt-1 text-sm text-zinc-400">
          New vendor layout detected. The AI has proposed a field extraction schema.
          Review and approve to register it and reprocess the document.
        </p>
      </div>

      <Card className="border-amber-900/50 bg-amber-950/20 ring-1 ring-inset ring-amber-900/40">
        <CardContent className="flex items-start gap-3 p-4">
          <ShieldWarningIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" weight="fill" />
          <div>
            <p className="text-sm font-medium text-amber-300">Awaiting Human Verification</p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              Vendor: <strong className="text-amber-300">{data.proposed_schema.vendor_name}</strong>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Proposed schema fields */}
      <Card className="border-zinc-800 bg-zinc-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            Proposed Extraction Schema
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {data.proposed_schema.fields.map((field, idx) => (
            <div
              key={field.key}
              className={`flex items-center justify-between px-4 py-3 ${
                idx < data.proposed_schema.fields.length - 1 ? "border-b border-zinc-800/50" : ""
              }`}
            >
              <div className="flex flex-col gap-0.5">
                <span className="font-mono text-sm text-zinc-200">{field.key}</span>
                <span className="text-xs text-zinc-500">{field.description}</span>
              </div>
              <Badge
                variant="outline"
                className="border-zinc-700 bg-zinc-900 font-mono text-[10px] text-zinc-400"
              >
                {field.type}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {approveError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-950/20 px-3 py-2 text-xs text-red-300">
          <XCircleIcon className="h-4 w-4 shrink-0" weight="fill" />
          {approveError}
        </div>
      )}

      {/* The Approve Button */}
      <div className="pt-4 flex justify-end">
        <Button
          onClick={handleApprove}
          disabled={isApproving}
          className="h-10 gap-2 bg-emerald-600 font-medium text-white hover:bg-emerald-500"
        >
          {isApproving ? (
            <SpinnerGapIcon className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircleIcon weight="bold" className="h-4 w-4" />
          )}
          {isApproving ? "Approving..." : "Approve Layout & Persist"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function ValidationStudioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: jobId } = use(params);
  const { setOpen } = useSidebar();
  const { job, isLoading, error, refetch } = useJob(jobId);
  const splitContainerRef = React.useRef<HTMLDivElement | null>(null);
  const [leftPaneWidth, setLeftPaneWidth] = React.useState(46);
  const [isResizing, setIsResizing] = React.useState(false);

  // Collapse sidebar for full-screen studio
  React.useEffect(() => {
    setOpen(false);
  }, [setOpen]);

  React.useEffect(() => {
    if (!isResizing) return;

    function handlePointerMove(event: PointerEvent) {
      const container = splitContainerRef.current;
      if (!container) return;

      const bounds = container.getBoundingClientRect();
      if (bounds.width <= 0) return;

      const rawPercentage = ((event.clientX - bounds.left) / bounds.width) * 100;
      const clampedPercentage = Math.min(65, Math.max(35, rawPercentage));
      setLeftPaneWidth(clampedPercentage);
    }

    function handlePointerUp() {
      setIsResizing(false);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [isResizing]);

  const isWaiting = job?.status === "WAITING_HUMAN";
  const isCompleted = job?.status === "COMPLETED" || job?.status === "DELIVERY_FAILED";
  const isFailed = job?.status === "FAILED";
  const isActive = job?.status === "PENDING" || job?.status === "PROCESSING";

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Top Application Bar */}
      <header className="z-10 flex h-14 w-full flex-none items-center justify-between overflow-hidden border-b border-zinc-800 bg-zinc-950 px-4">
        <div className="flex items-center gap-4">
          <SidebarTrigger className="-ml-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100" />
          <Separator orientation="vertical" className="hidden h-4 bg-zinc-800 md:block" />
          <Link href="/dashboard" className="text-zinc-500 transition-colors hover:text-zinc-300">
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <Separator orientation="vertical" className="h-6 bg-zinc-800" />
          <div className="flex items-center gap-2">
            <CpuIcon className="h-5 w-5 text-emerald-500" />
            <h1 className="text-sm font-medium tracking-wide">AI VALIDATION STUDIO</h1>
          </div>
          {job && (
            <>
              <Separator orientation="vertical" className="h-4 bg-zinc-800" />
              <span className="font-mono text-xs text-zinc-500">
                {job.job_id.split("-")[0].toUpperCase()}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-3">
          {job?.vendor_detected && (
            <Badge variant="outline" className="border-zinc-800 bg-zinc-900 font-mono text-xs text-zinc-400">
              {job.vendor_detected}
            </Badge>
          )}
          {isActive && (
            <Badge variant="outline" className="border-blue-900/50 bg-blue-950/30 text-blue-400">
              <SpinnerGapIcon className="mr-1 h-3.5 w-3.5 animate-spin" />
              {job?.status}
            </Badge>
          )}
          {isWaiting && (
            <Badge variant="outline" className="border-amber-900/50 bg-amber-950/30 text-amber-400">
              <ShieldWarningIcon className="mr-1 h-3.5 w-3.5" weight="fill" />
              AWAITING REVIEW
            </Badge>
          )}
          {isCompleted && (
            <Badge variant="outline" className="border-emerald-900/50 bg-emerald-950/30 text-emerald-400">
              <CheckCircleIcon className="mr-1 h-3.5 w-3.5" weight="fill" />
              COMPLETED
            </Badge>
          )}
          {isFailed && (
            <Badge variant="outline" className="border-red-900/50 bg-red-950/30 text-red-400">
              <XCircleIcon className="mr-1 h-3.5 w-3.5" weight="fill" />
              FAILED
            </Badge>
          )}
        </div>
      </header>

      {/* 50/50 Split View */}
      <main ref={splitContainerRef} className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left: PDF Viewer */}
        <section
          className="relative flex min-w-0 flex-col bg-zinc-950"
          style={{ width: `${leftPaneWidth}%` }}
        >
          {isLoading || !job ? (
            <div className="flex flex-1 items-center justify-center text-zinc-500">
              <SpinnerGapIcon className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <PdfViewer job={job} />
          )}
        </section>

        <div
          className={`group relative flex w-4 shrink-0 cursor-col-resize items-center justify-center bg-zinc-950 transition-colors ${
            isResizing ? "bg-zinc-900" : "hover:bg-zinc-900/70"
          }`}
          onPointerDown={(event) => {
            event.preventDefault();
            setIsResizing(true);
          }}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize PDF and validation panels"
        >
          <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-zinc-800" />
          <div
            className={`relative z-10 flex h-14 w-2 items-center justify-center rounded-full border border-zinc-800 bg-zinc-950 ${
              isResizing ? "shadow-[0_0_0_1px_rgba(16,185,129,0.25)]" : ""
            }`}
          >
            <div className="flex flex-col gap-1">
              <span className="h-1 w-1 rounded-full bg-zinc-500 transition-colors group-hover:bg-zinc-300" />
              <span className="h-1 w-1 rounded-full bg-zinc-500 transition-colors group-hover:bg-zinc-300" />
              <span className="h-1 w-1 rounded-full bg-zinc-500 transition-colors group-hover:bg-zinc-300" />
            </div>
          </div>
        </div>

        {/* Right: Extraction Report */}
        <section
          className="flex min-h-0 min-w-0 flex-col bg-zinc-950"
          style={{ width: `${100 - leftPaneWidth}%` }}
        >
          <div className="flex-1 overflow-y-auto min-h-0">
            {/* Loading */}
            {isLoading && <LoadingPanel />}

            {/* Error from hook */}
            {!isLoading && error && (
              <div className="flex flex-col items-center justify-center gap-3 p-12 text-center">
                <XCircleIcon className="h-10 w-10 text-red-400" weight="fill" />
                <p className="text-sm text-red-300">{error}</p>
                <p className="text-xs text-zinc-500">
                  Make sure the backend is running.
                </p>
              </div>
            )}

            {/* Active (PENDING / PROCESSING) */}
            {!isLoading && !error && isActive && (
              <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-blue-900/50 bg-blue-950/30">
                  <SpinnerGapIcon className="h-7 w-7 animate-spin text-blue-400" />
                </div>
                <p className="text-sm font-medium text-zinc-200">
                  {job?.status === "PENDING" ? "Job queued" : "AI pipeline processing…"}
                </p>
                <p className="text-xs text-zinc-500">
                  This page will update automatically. No need to refresh.
                </p>
              </div>
            )}

            {/* WAITING_HUMAN */}
            {!isLoading && !error && isWaiting && job?.extracted_data && (
              <WaitingHumanPanel
                jobId={jobId}
                data={job.extracted_data as WaitingHumanData}
                onApproved={refetch}
              />
            )}

            {/* COMPLETED / DELIVERY_FAILED */}
            {!isLoading && !error && isCompleted && job?.extracted_data && (
              <CompletedPanel data={job.extracted_data as ExtractedData} />
            )}

            {/* FAILED */}
            {!isLoading && !error && isFailed && (
              <div className="flex flex-col gap-4 p-8">
                <h2 className="text-xl font-semibold text-red-300">Processing Failed</h2>
                <Card className="border-red-900/50 bg-red-950/20">
                  <CardContent className="p-5">
                    <p className="font-mono text-xs text-red-200 whitespace-pre-wrap">
                      {job?.error_log ?? "Unknown error — check worker logs."}
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

          {/* Bottom Action Bar */}
          <div className="flex flex-none items-center justify-between border-t border-zinc-800 bg-zinc-950/80 p-4 backdrop-blur-sm">
            <div className="font-mono text-xs text-zinc-500">
              {job ? `Updated ${new Date(job.updated_at).toLocaleTimeString()}` : "—"}
            </div>
            <div className="flex items-center gap-3">
              {isCompleted && (
                <Button variant="ghost" className="h-10 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100">
                  Force Clear
                </Button>
              )}
              {(isCompleted || isFailed) && (
                <Button
                  className="h-10 gap-2 bg-red-600 font-medium text-white hover:bg-red-500"
                  variant="destructive"
                >
                  <XCircleIcon className="h-4 w-4" weight="bold" />
                  Reject Document
                </Button>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
