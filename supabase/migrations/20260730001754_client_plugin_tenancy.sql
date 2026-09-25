-- MVP client tenancy for shared plugin-driven workflows.

ALTER TABLE processing_jobs
ADD COLUMN IF NOT EXISTS client_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE document_registry
ADD COLUMN IF NOT EXISTS client_id TEXT NOT NULL DEFAULT 'default';

UPDATE processing_jobs
SET client_id = 'default'
WHERE client_id IS NULL;

UPDATE document_registry
SET client_id = 'default'
WHERE client_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_vendor_layout'
          AND conrelid = 'document_registry'::regclass
    ) THEN
        ALTER TABLE document_registry DROP CONSTRAINT unique_vendor_layout;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_client_vendor_layout'
          AND conrelid = 'document_registry'::regclass
    ) THEN
        ALTER TABLE document_registry
        ADD CONSTRAINT unique_client_vendor_layout
        UNIQUE (client_id, vendor_name, fingerprint_hash);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_processing_jobs_client_status_created_at
ON processing_jobs (client_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_registry_client_active
ON document_registry (client_id, is_active);
