"use client";

import * as React from "react";

import { getDossier } from "@/lib/api";
import type { DossierDetail } from "@/lib/types";

export function useDossier(caseId: string, clientId: string, pollInterval = 4000) {
  const [dossier, setDossier] = React.useState<DossierDetail | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [tick, setTick] = React.useState(0);

  const refetch = React.useCallback(() => setTick((value) => value + 1), []);

  React.useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!caseId) return;
      try {
        const result = await getDossier(caseId, clientId);
        if (!cancelled) {
          setDossier(result);
          setError(null);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Failed to load dossier");
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
  }, [caseId, clientId, pollInterval, tick]);

  return { dossier, isLoading, error, refetch };
}
