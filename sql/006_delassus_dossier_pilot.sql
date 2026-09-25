-- Delassus dossier domain, tenant-correct reference data, and reliable outbox.
-- Additive for existing invoice jobs; run after 005_client_plugin_tenancy.sql.

CREATE TABLE IF NOT EXISTS dossier_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    external_reference TEXT,
    workflow_id TEXT NOT NULL,
    workflow_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INGESTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dossier_cases_status_check CHECK (
        status IN ('INGESTED', 'PROCESSING', 'AWAITING_REVIEW', 'RESOLVED', 'FAILED')
    )
);

CREATE TABLE IF NOT EXISTS document_artifacts (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    source_artifact_id UUID REFERENCES document_artifacts(document_id) ON DELETE CASCADE,
    artifact_kind TEXT NOT NULL DEFAULT 'SOURCE',
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    page_start INT NOT NULL DEFAULT 1,
    page_end INT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    classification_confidence NUMERIC(5, 4),
    status TEXT NOT NULL DEFAULT 'PENDING',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT document_artifacts_kind_check CHECK (
        artifact_kind IN ('SOURCE', 'SEGMENT')
    ),
    CONSTRAINT document_artifacts_type_check CHECK (
        document_type IN (
            'DUM_MLV',
            'DUA',
            'BAD',
            'BILL_OF_LADING',
            'FREIGHT_INVOICE',
            'SUPPLIER_DOCUMENT',
            'UNKNOWN'
        )
    ),
    CONSTRAINT document_artifacts_status_check CHECK (
        status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
    ),
    CONSTRAINT document_artifacts_page_range_check CHECK (
        page_start >= 1 AND page_end >= page_start
    )
);

ALTER TABLE processing_jobs
    ADD COLUMN IF NOT EXISTS case_id UUID REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS document_artifact_id UUID REFERENCES document_artifacts(document_id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS workflow_id TEXT,
    ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_attempts INT NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE TABLE IF NOT EXISTS extraction_results (
    extraction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document_artifacts(document_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    run_id UUID NOT NULL DEFAULT gen_random_uuid(),
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    normalized_data JSONB NOT NULL,
    overall_confidence NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_refs (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extraction_results(extraction_id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES document_artifacts(document_id) ON DELETE CASCADE,
    field_path TEXT NOT NULL,
    page INT NOT NULL,
    source_text TEXT NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    bbox JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT evidence_refs_page_check CHECK (page >= 1),
    CONSTRAINT evidence_refs_confidence_check CHECK (
        confidence >= 0 AND confidence <= 1
    )
);

CREATE TABLE IF NOT EXISTS decision_results (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    decision_version INT NOT NULL,
    status TEXT NOT NULL,
    ruleset_id TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    summary TEXT NOT NULL,
    discrepancies JSONB NOT NULL DEFAULT '[]'::JSONB,
    report_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT decision_results_status_check CHECK (
        status IN ('READY', 'BLOCKED', 'REVIEW_REQUIRED')
    ),
    CONSTRAINT decision_results_case_version_key UNIQUE (case_id, decision_version)
);

CREATE TABLE IF NOT EXISTS review_tasks (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    decision_id UUID NOT NULL REFERENCES decision_results(decision_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    resolution TEXT,
    comment TEXT,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT review_tasks_status_check CHECK (
        status IN ('PENDING', 'RESOLVED', 'CANCELLED')
    ),
    CONSTRAINT review_tasks_resolution_check CHECK (
        resolution IS NULL OR resolution IN ('APPROVED', 'REJECTED', 'OVERRIDDEN')
    )
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    aggregate_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    publish_attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT outbox_events_status_check CHECK (
        status IN ('PENDING', 'PUBLISHING', 'PUBLISHED', 'FAILED')
    )
);

ALTER TABLE erp_purchase_orders
    ADD COLUMN IF NOT EXISTS client_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE erp_po_lines
    ADD COLUMN IF NOT EXISTS client_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE erp_goods_receipts
    ADD COLUMN IF NOT EXISTS client_id TEXT NOT NULL DEFAULT 'default';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_po_lines_po_number_fkey'
          AND conrelid = 'erp_po_lines'::regclass
    ) THEN
        ALTER TABLE erp_po_lines DROP CONSTRAINT erp_po_lines_po_number_fkey;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_goods_receipts_po_number_fkey'
          AND conrelid = 'erp_goods_receipts'::regclass
    ) THEN
        ALTER TABLE erp_goods_receipts DROP CONSTRAINT erp_goods_receipts_po_number_fkey;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_purchase_orders_pkey'
          AND conrelid = 'erp_purchase_orders'::regclass
    ) THEN
        ALTER TABLE erp_purchase_orders DROP CONSTRAINT erp_purchase_orders_pkey;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_purchase_orders_pkey'
          AND conrelid = 'erp_purchase_orders'::regclass
    ) THEN
        ALTER TABLE erp_purchase_orders
            ADD CONSTRAINT erp_purchase_orders_pkey
            PRIMARY KEY (client_id, po_number);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_po_lines_client_po_fkey'
          AND conrelid = 'erp_po_lines'::regclass
    ) THEN
        ALTER TABLE erp_po_lines
            ADD CONSTRAINT erp_po_lines_client_po_fkey
            FOREIGN KEY (client_id, po_number)
            REFERENCES erp_purchase_orders(client_id, po_number);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'erp_goods_receipts_client_po_fkey'
          AND conrelid = 'erp_goods_receipts'::regclass
    ) THEN
        ALTER TABLE erp_goods_receipts
            ADD CONSTRAINT erp_goods_receipts_client_po_fkey
            FOREIGN KEY (client_id, po_number)
            REFERENCES erp_purchase_orders(client_id, po_number);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_dossier_cases_client_created
    ON dossier_cases (client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dossier_cases_client_status_created
    ON dossier_cases (client_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_artifacts_case_active
    ON document_artifacts (case_id, is_active, page_start);

CREATE INDEX IF NOT EXISTS idx_document_artifacts_source
    ON document_artifacts (source_artifact_id, is_active);

CREATE UNIQUE INDEX IF NOT EXISTS idx_document_source_case_hash
    ON document_artifacts (case_id, sha256)
    WHERE artifact_kind = 'SOURCE';

CREATE INDEX IF NOT EXISTS idx_extraction_results_document_created
    ON extraction_results (document_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_refs_document_field
    ON evidence_refs (document_id, field_path);

CREATE INDEX IF NOT EXISTS idx_review_tasks_case_status
    ON review_tasks (case_id, status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_review_tasks_case_idempotency
    ON review_tasks (case_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_events_case_created
    ON audit_events (case_id, created_at);

CREATE INDEX IF NOT EXISTS idx_outbox_pending_available
    ON outbox_events (status, available_at)
    WHERE status = 'PENDING';

CREATE UNIQUE INDEX IF NOT EXISTS idx_processing_jobs_idempotency
    ON processing_jobs (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_processing_jobs_case_status
    ON processing_jobs (case_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_erp_purchase_orders_client_po
    ON erp_purchase_orders (client_id, po_number);

CREATE INDEX IF NOT EXISTS idx_erp_po_lines_client_po
    ON erp_po_lines (client_id, po_number);

CREATE INDEX IF NOT EXISTS idx_erp_goods_receipts_client_po
    ON erp_goods_receipts (client_id, po_number);
