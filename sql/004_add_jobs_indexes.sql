-- ============================================================
-- 004_add_jobs_indexes.sql
-- Performance optimization for efficient querying and pagination
-- on the processing_jobs table.
-- ============================================================

-- Index to optimize querying jobs by status, ordered by created_at DESC (e.g. /jobs?status=PENDING)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_status_created_desc
ON processing_jobs (status, created_at DESC);

-- Index to optimize querying all jobs, ordered by created_at DESC (e.g. /jobs without status filter)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_created_desc
ON processing_jobs (created_at DESC);
