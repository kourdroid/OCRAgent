-- Optimizations for /jobs endpoint

-- Index for filtering by status and sorting by created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_status_created_at
ON processing_jobs (status, created_at DESC);

-- Index for just sorting by created_at DESC (when status is not provided)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_created_at
ON processing_jobs (created_at DESC);
