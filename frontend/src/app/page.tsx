"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  MagnifyingGlassIcon,
  SpinnerGapIcon,
  FilePdfIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import { UploadSimpleIcon } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useJobs } from "@/hooks/use-jobs";
import type { Job, JobStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  JobStatus,
  { label: string; className: string }
> = {
  PENDING:        { label: "Pending",   className: "bg-zinc-900/50 text-zinc-400 border-zinc-700/50" },
  PROCESSING:     { label: "Processing",className: "bg-blue-950/40 text-blue-400 border-blue-900/60" },
  WAITING_HUMAN:  { label: "Awaiting",  className: "bg-amber-950/50 text-amber-400 border-amber-800/50" },
  COMPLETED:      { label: "Cleared",   className: "bg-emerald-950/50 text-emerald-400 border-emerald-800/50" },
  FAILED:         { label: "Failed",    className: "bg-red-950/50 text-red-400 border-red-800/50" },
  DELIVERY_FAILED:{ label: "Blocked",   className: "bg-red-950/50 text-red-400 border-red-800/50" },
};

type TabFilter = "all" | "action" | "warehouse" | "cleared";

function filterJobs(jobs: Job[], tab: TabFilter, query: string): Job[] {
  let filtered = jobs;

  if (tab === "action") {
    filtered = filtered.filter((j) =>
      ["WAITING_HUMAN", "FAILED", "DELIVERY_FAILED"].includes(j.status),
    );
  } else if (tab === "warehouse") {
    filtered = filtered.filter((j) => j.status === "PENDING" || j.status === "PROCESSING");
  } else if (tab === "cleared") {
    filtered = filtered.filter((j) => j.status === "COMPLETED");
  }

  if (query) {
    const q = query.toLowerCase();
    filtered = filtered.filter(
      (j) =>
        j.job_id.toLowerCase().includes(q) ||
        (j.vendor_detected ?? "").toLowerCase().includes(q),
    );
  }

  return filtered;
}

export default function CommandCenterPage() {
  const router = useRouter();
  const { jobs, isLoading, error } = useJobs({ pollInterval: 5000 });
  const [tab, setTab] = React.useState<TabFilter>("all");
  const [query, setQuery] = React.useState("");

  const displayed = filterJobs(jobs, tab, query);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-7xl px-6 py-8 w-full">
        <header className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <SidebarTrigger className="-ml-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100" />
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800">
              <div className="h-4 w-4 rounded-sm bg-gradient-to-br from-zinc-100 to-zinc-400" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Ironclad Command</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative w-80">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <Input
                id="command-center-search"
                placeholder="Search jobs, vendors…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="h-10 border-zinc-800 bg-zinc-900/50 pl-10 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-700 focus:ring-zinc-700"
              />
            </div>
            <Button
              id="go-to-dashboard-btn"
              onClick={() => router.push("/dashboard")}
              className="h-10 gap-2 bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
            >
              <UploadSimpleIcon className="h-4 w-4" weight="bold" />
              <span className="text-sm font-medium">Upload Documents</span>
            </Button>
          </div>
        </header>

        <div className="mb-6">
          <Tabs value={tab} onValueChange={(v) => setTab(v as TabFilter)} className="w-full">
            <TabsList className="h-auto gap-1 border-b border-zinc-800 bg-transparent p-0">
              {[
                { value: "all",       label: "All Jobs" },
                { value: "action",    label: "Action Required" },
                { value: "warehouse", label: "In Progress" },
                { value: "cleared",   label: "Cleared" },
              ].map(({ value, label }) => (
                <TabsTrigger
                  key={value}
                  value={value}
                  className="relative h-9 rounded-none border-b-2 border-transparent px-4 text-sm font-medium text-zinc-400 data-[state=active]:border-zinc-100 data-[state=active]:text-zinc-100 data-[state=active]:shadow-none"
                >
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        <div className="overflow-hidden rounded-lg border border-zinc-800">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                {["Job ID", "Vendor", "Type", "Time", "Status"].map((h) => (
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
              {/* Loading */}
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={5} className="py-12 text-center">
                    <div className="flex items-center justify-center gap-2 text-zinc-500">
                      <SpinnerGapIcon className="h-5 w-5 animate-spin" />
                      <span className="text-sm">Loading jobs…</span>
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {/* Error */}
              {!isLoading && error && (
                <TableRow>
                  <TableCell colSpan={5} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <XCircleIcon className="h-8 w-8 text-red-400" weight="fill" />
                      <span className="text-sm text-red-300">{error}</span>
                      <span className="text-xs text-zinc-500">Backend not reachable at localhost:8000</span>
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {/* Empty */}
              {!isLoading && !error && displayed.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <FilePdfIcon className="h-8 w-8 text-zinc-700" weight="light" />
                      <span className="text-sm text-zinc-500">No jobs found</span>
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {/* Data rows */}
              {!isLoading &&
                !error &&
                displayed.map((job) => {
                  const cfg = STATUS_CONFIG[job.status];
                  const relTime = (() => {
                    const diff = Date.now() - new Date(job.created_at).getTime();
                    const m = Math.floor(diff / 60000);
                    if (m < 60) return `${m}m ago`;
                    return `${Math.floor(m / 60)}h ago`;
                  })();

                  return (
                    <TableRow
                      key={job.job_id}
                      id={`cmd-row-${job.job_id}`}
                      onClick={() => router.push(`/validation/${job.job_id}`)}
                      className="cursor-pointer border-zinc-800/50 transition-colors hover:bg-zinc-900/30"
                    >
                      <TableCell className="px-4 py-3 font-mono text-xs text-zinc-300">
                        {job.job_id.split("-")[0].toUpperCase()}
                      </TableCell>
                      <TableCell className="px-4 py-3 text-sm text-zinc-100">
                        {job.vendor_detected ?? (
                          <span className="italic text-zinc-600">Unknown</span>
                        )}
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <span className="inline-flex items-center rounded-md bg-zinc-800/50 px-2 py-0.5 text-xs font-medium text-zinc-400">
                          INVOICE
                        </span>
                      </TableCell>
                      <TableCell className="px-4 py-3 font-mono text-sm text-zinc-400">
                        {relTime}
                      </TableCell>
                      <TableCell className="px-4 py-3">
                        <Badge
                          variant="outline"
                          className={`rounded-md border px-2 py-0.5 text-xs font-medium ${cfg.className}`}
                        >
                          {cfg.label}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
