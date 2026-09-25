-- ============================================================
-- 004_core_mvp_indexes_constraints.sql
-- Additive indexes and status guardrails for the MVP workflow.
-- Run after 003_erp_tables.sql.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status_created_at
    ON processing_jobs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at
    ON processing_jobs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_registry_is_active
    ON document_registry (is_active);

CREATE INDEX IF NOT EXISTS idx_document_registry_vendor_name
    ON document_registry (vendor_name);

CREATE INDEX IF NOT EXISTS idx_erp_po_lines_po_number
    ON erp_po_lines (po_number);

CREATE INDEX IF NOT EXISTS idx_erp_goods_receipts_po_number
    ON erp_goods_receipts (po_number);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'processing_jobs_status_check'
    ) THEN
        ALTER TABLE processing_jobs
            ADD CONSTRAINT processing_jobs_status_check
            CHECK (
                status IN (
                    'PENDING',
                    'PROCESSING',
                    'WAITING_HUMAN',
                    'COMPLETED',
                    'FAILED',
                    'DELIVERY_FAILED'
                )
            ) NOT VALID;
    END IF;
END
$$;

