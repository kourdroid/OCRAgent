-- Migration: Add multi-layout support columns and composite unique constraint
-- This brings a live database in sync with the updated 001_registry_jobs.sql schema.

-- 1. Add missing columns (idempotent via IF NOT EXISTS)
ALTER TABLE document_registry ADD COLUMN IF NOT EXISTS fingerprint_hash TEXT;
ALTER TABLE document_registry ADD COLUMN IF NOT EXISTS ocr_text_cache TEXT;

-- 2. Drop the old 1:1 vendor_name uniqueness if it still exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'document_registry_vendor_name_key'
    ) THEN
        ALTER TABLE document_registry DROP CONSTRAINT document_registry_vendor_name_key;
    END IF;
END
$$;

-- 3. Add the composite unique constraint (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'unique_vendor_layout'
    ) THEN
        ALTER TABLE document_registry
            ADD CONSTRAINT unique_vendor_layout UNIQUE (vendor_name, fingerprint_hash);
    END IF;
END
$$;
