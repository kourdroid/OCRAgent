# Ironclad Current Readiness

## Implemented

- Legacy invoice schema onboarding, extraction, reconciliation, and webhook flow.
- Client-scoped schema lookup and invoice jobs.
- Delassus dossier domain with source files, classified page ranges, normalized
  facts, evidence, decisions, reviews, audit events, and reports.
- Transactional database outbox for dossier work.
- Idempotent dossier processing with persisted retries and terminal failure.
- Shared frontend for dossier intake, evidence review, resolution,
  reprocessing, and report download.
- OpenAI-compatible provider adapter separated from core workflow logic.
- Docker Compose services for Redis, API, worker, outbox dispatcher, and
  frontend.

## Verified Locally

- Backend unit/API tests.
- Python compilation.
- Frontend lint and production build.
- Docker Compose configuration parsing.
- Backend and frontend Docker image builds.
- Redis and frontend container health checks.
- All six migrations against a clean disposable PostgreSQL 17 database.
- Tenant-scoped ERP uniqueness and stale outbox lease recovery.
- Desktop and mobile dossier intake layouts without horizontal overflow.

## External Verification Still Required

- Apply and inspect migration `006` against the linked Supabase project with an
  account that has migration privileges.
- Restore a reachable `DATABASE_URL`; the current external database credentials
  make the API unhealthy and prevent worker/outbox startup.
- Execute a real provider-backed Delassus dossier from upload through report.
- Review the seven current Delassus PDFs as smoke cases; do not treat them as an
  accuracy benchmark.

## Pilot Boundaries

- Every generated decision requires human resolution.
- Exact conflicts in declaration, bill-of-lading, or container identifiers can
  produce `BLOCKED`.
- Unknown types, low confidence, missing facts, or unconfirmed policy produce
  `REVIEW_REQUIRED`.
- Automatic `READY` is disabled until Delassus confirms the ruleset.
- Authentication, RLS, private storage, and production operations remain
  production gates.

## Product Direction

Ironclad should remain an auditable dossier decision layer rather than a
generic OCR product. Cloud and local OCR models are infrastructure adapters;
the reusable value is cross-document reconciliation, evidence, conservative
decisioning, and review history.
