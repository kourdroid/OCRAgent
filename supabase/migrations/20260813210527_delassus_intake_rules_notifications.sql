-- Delassus operational administration: provenance, confirmed rules, and inbox notifications.
-- This migration is additive. Existing cases remain valid and are treated as legacy web uploads.

CREATE TABLE IF NOT EXISTS app_users (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'PLATFORM_SUPER_ADMIN',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT app_users_role_check CHECK (role = 'PLATFORM_SUPER_ADMIN')
);

CREATE TABLE IF NOT EXISTS source_parties (
    party_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    name TEXT NOT NULL,
    scope TEXT NOT NULL,
    party_type TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT source_parties_scope_check CHECK (scope IN ('INTERNAL', 'EXTERNAL')),
    CONSTRAINT source_parties_type_check CHECK (
        (scope = 'EXTERNAL' AND party_type IN ('INSTITUTION', 'SERVICE_PROVIDER', 'CLIENT', 'SUPPLIER', 'OTHER'))
        OR (scope = 'INTERNAL' AND party_type IN ('DIRECTION', 'FINANCE', 'COMMERCIAL', 'OTHER'))
    ),
    CONSTRAINT source_parties_client_name_key UNIQUE (client_id, name)
);

CREATE TABLE IF NOT EXISTS intake_submissions (
    intake_submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    intake_channel TEXT NOT NULL,
    sender_party_id UUID REFERENCES source_parties(party_id) ON DELETE SET NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    channel_reference TEXT,
    idempotency_key TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT intake_submissions_channel_check CHECK (intake_channel IN ('WEB_UPLOAD', 'API'))
);

ALTER TABLE document_artifacts
    ADD COLUMN IF NOT EXISTS intake_submission_id UUID REFERENCES intake_submissions(intake_submission_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS issuer_party_id UUID REFERENCES source_parties(party_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS provenance_status TEXT NOT NULL DEFAULT 'MISSING_BOTH';

ALTER TABLE document_artifacts
    DROP CONSTRAINT IF EXISTS document_artifacts_provenance_status_check;

ALTER TABLE document_artifacts
    ADD CONSTRAINT document_artifacts_provenance_status_check CHECK (
        provenance_status IN ('COMPLETE', 'MISSING_SENDER', 'MISSING_ISSUER', 'MISSING_BOTH')
    );

CREATE TABLE IF NOT EXISTS rule_sets (
    ruleset_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    version INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    name TEXT NOT NULL,
    confirmation_comment TEXT,
    confirmed_by UUID REFERENCES app_users(user_id) ON DELETE SET NULL,
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rule_sets_status_check CHECK (status IN ('DRAFT', 'ACTIVE', 'RETIRED')),
    CONSTRAINT rule_sets_version_key UNIQUE (client_id, workflow_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rule_sets_one_active
    ON rule_sets (client_id, workflow_id)
    WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS rule_definitions (
    rule_id TEXT PRIMARY KEY,
    ruleset_id TEXT NOT NULL REFERENCES rule_sets(ruleset_id) ON DELETE CASCADE,
    template_type TEXT NOT NULL,
    name TEXT NOT NULL,
    field_path TEXT,
    authoritative_document_type TEXT,
    compared_document_type TEXT,
    parameters JSONB NOT NULL DEFAULT '{}'::JSONB,
    severity TEXT NOT NULL DEFAULT 'warning',
    failure_outcome TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    display_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rule_definitions_template_check CHECK (
        template_type IN ('REQUIRED_DOCUMENT', 'FIELD_REQUIRED', 'EXACT_MATCH', 'NUMERIC_TOLERANCE', 'DATE_WINDOW', 'AUTHORITY_PRECEDENCE')
    ),
    CONSTRAINT rule_definitions_severity_check CHECK (severity IN ('info', 'warning', 'critical')),
    CONSTRAINT rule_definitions_outcome_check CHECK (failure_outcome IN ('BLOCKED', 'REVIEW_REQUIRED'))
);

CREATE TABLE IF NOT EXISTS rule_evaluation_results (
    evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decision_results(decision_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    message TEXT NOT NULL,
    compared_values JSONB NOT NULL DEFAULT '[]'::JSONB,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rule_evaluation_results_outcome_check CHECK (outcome IN ('PASS', 'FAIL', 'REVIEW_REQUIRED', 'NOT_APPLICABLE'))
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    case_id UUID REFERENCES dossier_cases(case_id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    deduplication_key TEXT NOT NULL,
    read_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT notifications_type_check CHECK (notification_type IN ('DOSSIER_REVIEW_REQUIRED', 'DOSSIER_BLOCKED', 'PROCESSING_FAILED', 'DOSSIER_RESOLVED', 'RULESET_ACTIVATED')),
    CONSTRAINT notifications_severity_check CHECK (severity IN ('info', 'warning', 'critical')),
    CONSTRAINT notifications_deduplication_key UNIQUE (deduplication_key)
);

-- Existing source documents were created through the pre-provenance web workflow.
INSERT INTO intake_submissions (intake_submission_id, client_id, intake_channel, metadata)
SELECT gen_random_uuid(), d.client_id, 'WEB_UPLOAD',
       jsonb_build_object('legacy', true, 'legacy_source_document_id', d.document_id)
FROM document_artifacts d
WHERE d.artifact_kind = 'SOURCE'
  AND d.intake_submission_id IS NULL;

UPDATE document_artifacts d
SET intake_submission_id = i.intake_submission_id
FROM intake_submissions i
WHERE d.artifact_kind = 'SOURCE'
  AND d.intake_submission_id IS NULL
  AND (i.metadata ->> 'legacy_source_document_id')::UUID = d.document_id;

-- A legacy case has no trusted sender/issuer data. Keep that uncertainty explicit.
UPDATE document_artifacts
SET provenance_status = 'MISSING_BOTH'
WHERE artifact_kind = 'SOURCE'
  AND provenance_status IS NULL;

INSERT INTO rule_sets (ruleset_id, client_id, workflow_id, version, status, name, confirmation_comment)
VALUES (
    'delassus-pilot-draft-v1',
    'delassus',
    'morocco_import_dossier',
    1,
    'DRAFT',
    'Delassus pilot baseline checks',
    'Imported from the pre-managed workflow. Requires client confirmation before activation.'
)
ON CONFLICT (ruleset_id) DO NOTHING;

INSERT INTO rule_definitions (
    rule_id, ruleset_id, template_type, name, field_path,
    severity, failure_outcome, display_order
)
VALUES
    ('delassus-v1-declaration-number', 'delassus-pilot-draft-v1', 'EXACT_MATCH', 'Declaration number must match', 'declaration_number', 'critical', 'BLOCKED', 10),
    ('delassus-v1-bill-of-lading-number', 'delassus-pilot-draft-v1', 'EXACT_MATCH', 'Bill of lading number must match', 'bill_of_lading_number', 'critical', 'BLOCKED', 20),
    ('delassus-v1-container-number', 'delassus-pilot-draft-v1', 'EXACT_MATCH', 'Container number must match', 'container_number', 'critical', 'BLOCKED', 30)
ON CONFLICT (rule_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_source_parties_client_active
    ON source_parties (client_id, is_active, name);
CREATE INDEX IF NOT EXISTS idx_intake_submissions_client_received
    ON intake_submissions (client_id, received_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_intake_submissions_client_idempotency
    ON intake_submissions (client_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_document_artifacts_intake
    ON document_artifacts (intake_submission_id, artifact_kind);
CREATE INDEX IF NOT EXISTS idx_rule_definitions_ruleset_order
    ON rule_definitions (ruleset_id, display_order);
CREATE INDEX IF NOT EXISTS idx_rule_evaluation_decision
    ON rule_evaluation_results (decision_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_client_unread
    ON notifications (client_id, created_at DESC)
    WHERE read_at IS NULL;

ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE intake_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_evaluation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dossier_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_refs ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
