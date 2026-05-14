"use client";

import * as React from "react";
import { ingestDocument } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

const MAX_FILE_SIZE_MB = 50;

interface UseIngestResult {
  ingest: (file: File) => Promise<IngestResponse | null>;
  isUploading: boolean;
  error: string | null;
  result: IngestResponse | null;
  reset: () => void;
}

export function useIngest(): UseIngestResult {
  const [isUploading, setIsUploading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<IngestResponse | null>(null);

  const reset = React.useCallback(() => {
    setError(null);
    setResult(null);
  }, []);

  const ingest = React.useCallback(async (file: File): Promise<IngestResponse | null> => {
    // Client-side validation
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return null;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`File exceeds maximum size of ${MAX_FILE_SIZE_MB} MB.`);
      return null;
    }

    setError(null);
    setIsUploading(true);

    try {
      const response = await ingestDocument(file);
      setResult(response);
      return response;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setError(msg);
      return null;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return { ingest, isUploading, error, result, reset };
}
