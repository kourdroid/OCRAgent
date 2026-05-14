"use client";

import * as React from "react";
import { listJobs } from "@/lib/api";
import type { Job, JobStatus } from "@/lib/types";

interface UseJobsOptions {
  status?: JobStatus;
  limit?: number;
  pollInterval?: number; // ms — 0 disables polling
}

interface UseJobsResult {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useJobs({
  status,
  limit = 50,
  pollInterval = 5000,
}: UseJobsOptions = {}): UseJobsResult {
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);

  const refetch = React.useCallback(() => setTick((t) => t + 1), []);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await listJobs({ status, limit });
        if (!cancelled) {
          setJobs(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    setIsLoading(true);
    load();

    if (pollInterval > 0) {
      const id = setInterval(load, pollInterval);
      return () => {
        cancelled = true;
        clearInterval(id);
      };
    }
    return () => {
      cancelled = true;
    };
  }, [status, limit, pollInterval, tick]);

  return { jobs, isLoading, error, refetch };
}
