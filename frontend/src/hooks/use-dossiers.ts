"use client";

import * as React from "react";

import { listDossiers } from "@/lib/api";
import type { DossierSummary } from "@/lib/types";

export function useDossiers(clientId: string, pollInterval = 5000) {
  const [dossiers, setDossiers] = React.useState<DossierSummary[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);

  const refetch = React.useCallback(() => setTick((value) => value + 1), []);

  React.useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await listDossiers({ clientId, limit: 100 });
        if (!cancelled) {
          setDossiers(result);
          setError(null);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Failed to load dossiers");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    const interval = window.setInterval(() => void load(), pollInterval);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [clientId, pollInterval, tick]);

  return { dossiers, isLoading, error, refetch };
}
