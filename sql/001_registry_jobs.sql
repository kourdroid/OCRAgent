-- 1. The Registry: Stores the "Brain Patterns" for each vendor
CREATE TABLE document_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_name TEXT UNIQUE NOT NULL,
    fingerprint_hash TEXT,
    schema_definition JSONB NOT NULL,
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
