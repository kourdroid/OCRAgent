-- Optimize `GET /jobs` pagination queries
-- Adding these indexes allows PostgreSQL to use B-Tree backwards index scans,
-- turning O(N log N) file sorts into fast O(LIMIT) lookups.

-- Index for queries filtering by status: `SELECT ... WHERE status = $1 ORDER BY created_at DESC LIMIT ...`
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_status_created_at
ON processing_jobs (status, created_at DESC);

-- Index for queries without status filter: `SELECT ... ORDER BY created_at DESC LIMIT ...`
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_created_at
ON processing_jobs (created_at DESC);
