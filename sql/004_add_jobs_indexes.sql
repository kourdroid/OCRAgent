-- Migration: Add indexes to processing_jobs table for efficient querying

-- 1. Index for list_jobs queries filtering by status and ordering by created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_status_created_at
ON processing_jobs (status, created_at DESC);

-- 2. Index for list_jobs queries ordering by created_at DESC (without status filter)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_processing_jobs_created_at
ON processing_jobs (created_at DESC);
