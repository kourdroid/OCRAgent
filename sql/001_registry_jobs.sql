-- 1. The Registry: Stores the "Brain Patterns" for each vendor
CREATE TABLE document_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_name TEXT NOT NULL,
    fingerprint_hash TEXT,
    ocr_text_cache TEXT,
    schema_definition JSONB NOT NULL,
    CONSTRAINT unique_vendor_layout UNIQUE (vendor_name, fingerprint_hash),
    schema_version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. The Jobs: Tracks every file processed
CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT DEFAULT 'PENDING',
    file_url TEXT NOT NULL,
    vendor_detected TEXT,
    extracted_data JSONB,
    error_log TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Vector Support (Future Proofing)
CREATE EXTENSION IF NOT EXISTS vector;
