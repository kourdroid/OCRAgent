"use client";

import * as React from "react";
import { getJob } from "@/lib/api";
import type { Job } from "@/lib/types";

/** Statuses that mean the job is still in-flight and we should keep polling */
const ACTIVE_STATUSES = new Set(["PENDING", "PROCESSING"]);

interface UseJobResult {
  job: Job | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useJob(jobId: string | null, pollInterval = 3000): UseJobResult {
  const [job, setJob] = React.useState<Job | null>(null);
  const [isLoading, setIsLoading] = React.useState(!!jobId);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);

  const refetch = React.useCallback(() => setTick((t) => t + 1), []);

  React.useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    async function load() {
      try {
        const data = await getJob(jobId!);
        if (!cancelled) {
          setJob(data);
          setError(null);
          setIsLoading(false);

          // Keep polling only while the job is still in-flight
          if (ACTIVE_STATUSES.has(data.status) && pollInterval > 0) {
            timerId = setTimeout(load, pollInterval);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
    };
  }, [jobId, pollInterval, tick]);

  return { job, isLoading, error, refetch };
}
