# Ironclad-OCR Codebase Analysis

## Overview
Ironclad-OCR is a PDF invoice processing service built around FastAPI, Redis Streams, Supabase/Postgres, and LangGraph. The system uploads PDFs, splits merged documents, identifies vendors, discovers or reuses extraction schemas, and optionally runs deterministic ERP reconciliation before delivering results to a webhook.

## Architecture

### API
`src/api/routes.py` exposes:
- `POST /ingest` for PDF upload, local storage, splitting, job creation, and queueing.
- `GET /jobs/{job_id}` for job status lookup.
- `POST /approve` for human approval of proposed schemas and job requeueing.
- `GET /health` for Redis and database checks.

### Worker
`src/worker/worker.py` runs a long-lived Redis consumer loop. It loads the LangGraph workflow from `src/core/graph.py`, processes each message, and ACKs or fails jobs based on execution outcome.

### Core Workflow
`src/core/graph.py` defines the orchestration flow:
- `fingerprint_and_lookup` identifies the vendor and tries to match an existing schema.
- `discovery_agent` proposes a schema for unknown vendors.
- `human_hold` persists a proposed schema and stops for approval.
- `extract` runs schema-based extraction.
- `reconcile` compares extracted invoice data against ERP PO and receipt data.
- `deliver_webhook` sends the final payload outward.

### AI and Schema Layer
`src/core/nodes.py` uses OpenRouter through `openai.AsyncOpenAI` to:
- identify vendors,
- discover schemas,
- detect drift,
- extract structured data with dynamic Pydantic models.

`src/schemas.py` defines the invoice and registry schema models.

### Infrastructure
- `src/infrastructure/redis_queue.py` wraps Redis Streams.
- `src/infrastructure/supabase_repos.py` wraps Postgres access for jobs, schemas, and ERP tables.
- `src/infrastructure/webhook_client.py` posts completed payloads to an external webhook.
- `src/plugins/supply_chain.py` contains deterministic 3-way match logic.

## Key Observations

### Strengths
- Clear separation between API, worker, workflow, persistence, and plugin logic.
- Human-in-the-loop schema onboarding is built into the workflow.
- Deterministic reconciliation is isolated from the LLM path.
- Pydantic is used for runtime validation and dynamic schema shaping.

### Risks and Gaps
1. Redis retry handling is incomplete. The worker leaves transient failures unacked, but the queue reader only consumes `>` messages from `XREADGROUP`, which does not re-deliver pending entries automatically.
2. Drift handling appears partially wired. `detect_drift` and `schema_evolution_agent` exist, but the active graph path does not route through them.
3. The test suite is stale. Several tests still reference removed config fields and old helper functions.
4. Local validation is blocked by missing `asyncpg` in the current environment.
5. The API has no auth layer, so upload, approve, and status endpoints are open if the service is exposed.
6. Database access opens a fresh connection per repository call instead of using pooling.
7. The Redis consumer name is hardcoded, which makes scaling multiple workers unsafe.
8. `ApproveRequest.schema_definition` is only typed as `dict`, so malformed schemas can enter the registry.
9. Webhook delivery does not check non-2xx responses.
10. ERP tables lack indexes on `po_number`, which will hurt reconciliation as data grows.

## Data Flow
1. Upload PDF to `/ingest`.
2. Save file to `data/uploads`.
3. Split multi-invoice PDFs into chunks.
4. Create one job row per split file.
5. Enqueue each job to Redis Streams.
6. Worker consumes the message and runs vendor detection.
7. Known vendor: extract immediately.
8. Unknown vendor: discover schema and wait for approval.
9. On approval, schema is stored and the job is requeued.
10. After extraction, the payload is reconciled and sent to the webhook.

## Test State
- Full `pytest` currently fails during import because `asyncpg` is missing locally.
- Lightweight tests show partial success, but one graph test fails because it references a removed helper.

## Recommended Next Steps
1. Add Redis pending-message recovery or claim logic.
2. Wire drift detection into the active graph.
3. Update stale tests to the current code contracts.
4. Add auth for public endpoints.
5. Introduce DB pooling and configurable Redis consumer names.
6. Validate schema approval payloads with Pydantic.
7. Refresh docs and compose defaults to match current OpenRouter-based behavior.
