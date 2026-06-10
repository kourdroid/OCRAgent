-- 1. Index for filtering by status and sorting by created_at DESC
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status_created_at
ON processing_jobs (status, created_at DESC);

-- 2. Index for sorting by created_at DESC (when no status filter is applied)
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at
ON processing_jobs (created_at DESC);
