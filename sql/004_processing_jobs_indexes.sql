-- Migration: Add indexes to optimize /jobs API endpoint
-- Use CONCURRENTLY to avoid locking the table during index creation

-- Index for filtering by status and sorting by created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_status_created_at
ON processing_jobs (status, created_at DESC);

-- Index for sorting by created_at DESC when no status filter is applied
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_created_at
ON processing_jobs (created_at DESC);
