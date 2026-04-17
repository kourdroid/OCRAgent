# Ironclad-OCR

Ironclad-OCR is an asynchronous invoice ingestion and extraction service built for vendor PDFs that do not share a single stable layout. It combines:

- `FastAPI` for ingestion and status APIs
- `Redis Streams` for durable background job dispatch
- `Postgres / Supabase` for schema registry and job state
- `LangGraph` for orchestration
- `OpenRouter` via the `openai` Python SDK for vendor identification, schema discovery, and extraction
- deterministic ERP reconciliation for supply-chain workflows

The system is designed around a human-in-the-loop schema onboarding model:

1. A PDF is uploaded.
2. The worker identifies the vendor and tries to match an existing layout.
3. If the layout is known, extraction runs immediately.
4. If the layout is unknown, the system proposes a schema and pauses for approval.
5. After approval, the job is requeued and processed with the stored schema.

## What It Does

- Accepts PDF uploads through an API.
- Splits merged invoice packets into per-invoice jobs.
- Stores processing state in Postgres.
- Uses fuzzy header matching to reuse the best known vendor schema.
- Falls back to schema discovery for unseen layouts.
- Extracts structured JSON from PDFs.
- Optionally runs 3-way matching against ERP purchase order and goods receipt data.
- Delivers final results to an outbound webhook.
- Recovers Redis pending jobs after worker crashes using `XAUTOCLAIM`.

## Current Processing Flow

### 1. Ingestion
`POST /ingest`

- Accepts one PDF upload.
- Saves the file to `data/uploads/`.
- Runs PDF splitting to detect separate invoices inside a packet.
- Creates one `processing_jobs` row per split PDF.
- Enqueues one Redis Stream message per job.

### 2. Worker execution
`src/worker/worker.py`

- Reads new jobs from Redis Streams with consumer groups.
- Periodically claims stuck pending messages older than 10 minutes using `XAUTOCLAIM`.
- Runs the LangGraph workflow.
- Acknowledges successful and fatal jobs.
- Leaves transient failures unacked so they can be reclaimed later.

### 3. Schema lookup or discovery
`src/core/graph.py`

- `fingerprint_and_lookup` identifies vendor and header text.
- A normalized fuzzy match compares the current header to known layouts stored in `document_registry`.
- If a layout match is strong enough, extraction proceeds.
- Otherwise, `discovery_agent` proposes a new schema and the job moves to `WAITING_HUMAN`.

### 4. Human approval
`POST /approve`

- Stores the approved schema in the registry.
- Marks the original job as `PENDING`.
- Requeues the job for extraction.

### 5. Extraction and reconciliation

- Extraction runs against the approved vendor schema.
- The worker attempts ERP reconciliation using `po_number` or `order_reference`.
- Final payload is persisted and sent to the configured webhook.
- Webhook failures are recorded as `DELIVERY_FAILED` in the job table.

## Architecture

### API layer
- `src/api/app.py`: FastAPI app entrypoint
- `src/api/routes.py`: ingest, status, approval, health endpoints

### Core workflow
- `src/core/graph.py`: LangGraph orchestration
- `src/core/nodes.py`: LLM-backed vendor ID, schema discovery, extraction helpers
- `src/core/pdf_splitter.py`: packet splitting logic
- `src/core/state.py`: graph state contract

### Infrastructure
- `src/infrastructure/redis_queue.py`: Redis Streams wrapper with pending recovery
- `src/infrastructure/supabase_repos.py`: asyncpg-backed repositories with connection pooling
- `src/infrastructure/webhook_client.py`: outbound webhook delivery and error persistence

### Plugins
- `src/plugins/supply_chain.py`: deterministic 3-way match logic

### SQL
- `sql/001_registry_jobs.sql`: base tables
- `sql/002_add_multi_layout_support.sql`: multi-layout migration
- `sql/003_erp_tables.sql`: ERP reconciliation tables and seed data

## Job Statuses

The `processing_jobs.status` field currently uses these values in practice:

- `PENDING`: queued for worker processing
- `PROCESSING`: actively being processed by the worker
- `WAITING_HUMAN`: awaiting schema approval
- `COMPLETED`: extraction finished successfully
- `FAILED`: fatal processing failure
- `DELIVERY_FAILED`: extraction completed, but webhook delivery failed

## Requirements

- Python `3.11+`
- Redis `6.2+`
- PostgreSQL-compatible database or Supabase Postgres
- OpenRouter API key

Python dependencies are declared in `requirements.txt`:

- `fastapi`
- `uvicorn`
- `redis`
- `asyncpg`
- `langgraph`
- `openai`
- `pydantic`
- `pypdf`
- `aiofiles`
- `python-multipart`
- `python-dotenv`
- `httpx`
- `rich`

## Configuration

Environment is loaded from `.env` by `src/config.py`.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Yes | `""` | API key used for LLM calls |
| `MODEL_NAME` | No | `google/gemini-2.0-flash` | OpenRouter model name |
| `TEMPERATURE` | No | `0.1` | Model temperature |
| `DRIFT_THRESHOLD` | No | `0.8` | Reserved threshold config |
| `DATABASE_URL` | Yes for ingest/worker | none | Postgres connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `WEBHOOK_URL` | No | none | Final result delivery target |
| `DATA_DIR` | No | `./data` | Base directory for uploads and output |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

### Example `.env`

```env
OPENROUTER_API_KEY=your_openrouter_key
MODEL_NAME=google/gemini-2.0-flash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ironclad
REDIS_URL=redis://localhost:6379/0
WEBHOOK_URL=http://localhost:9000/webhook
DATA_DIR=./data
LOG_LEVEL=INFO
```

## Database Setup

Run the SQL files in this order:

1. `sql/001_registry_jobs.sql`
2. `sql/002_add_multi_layout_support.sql`
3. `sql/003_erp_tables.sql`

### Core tables

`document_registry`
- stores vendor layout schemas
- supports multiple layouts per vendor through `(vendor_name, fingerprint_hash)` uniqueness

`processing_jobs`
- stores file path, vendor, status, extracted payload, and errors

`erp_purchase_orders`, `erp_po_lines`, `erp_goods_receipts`
- support deterministic reconciliation

## Running Locally

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional dev dependencies:

```bash
pip install -r requirements-dev.txt
```

### 2. Start Redis

If Redis is already installed locally:

```bash
redis-server
```

Or via Docker Compose:

```bash
docker compose up -d redis
```

### 3. Prepare the database

- create a Postgres database
- run the SQL files under `sql/`
- set `DATABASE_URL`

### 4. Start the API

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the worker

```bash
python -m src.worker.worker
```

The API and worker are separate processes and both must be running for end-to-end processing.

## Running with Docker Compose

The repository includes `docker-compose.yml` with:

- `redis`
- `api`
- `worker`

Bring everything up:

```bash
docker compose up --build
```

Notes:

- `DATABASE_URL` must still point to a reachable Postgres database.
- The compose file still includes a legacy `GOOGLE_API_KEY` environment variable, but the current codepath uses `OPENROUTER_API_KEY`.

## API Reference

### `POST /ingest`

Uploads a PDF and returns one job ID per split invoice.

Request:
- multipart form-data
- field name: `file`

Example:

```bash
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@invoice.pdf"
```

Response:

```json
{
  "job_ids": [
    "2f26c8f2-5f7d-4134-94c7-dedbde1b5c8e"
  ]
}
```

### `GET /jobs/{job_id}`

Fetches the current database record for a job.

Example:

```bash
curl "http://localhost:8000/jobs/2f26c8f2-5f7d-4134-94c7-dedbde1b5c8e"
```

### `POST /approve`

Approves a proposed schema and requeues the job.

Example:

```bash
curl -X POST "http://localhost:8000/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "2f26c8f2-5f7d-4134-94c7-dedbde1b5c8e",
    "vendor_name": "LABEL_TECH",
    "schema_definition": {
      "vendor_name": "LABEL_TECH",
      "version": 1,
      "fields": [
        {
          "key": "invoice_number",
          "type": "str",
          "description": "Invoice identifier"
        },
        {
          "key": "invoice_date",
          "type": "date",
          "description": "Invoice date"
        },
        {
          "key": "line_items",
          "type": "list",
          "description": "Extracted line items"
        }
      ]
    }
  }'
```

### `GET /health`

Returns a Redis and database health report.

Example response:

```json
{
  "status": "ok",
  "redis": { "ok": true },
  "supabase": { "ok": true }
}
```

If the database is unavailable or missing tables, the endpoint returns `degraded` details.

## Packet Splitting

`src/core/pdf_splitter.py` uses heuristics to detect new invoice boundaries in merged PDFs by scanning page text for invoice-like headers. If a PDF appears to contain multiple invoices, each detected chunk becomes its own job.

This allows a single uploaded packet to fan out into multiple independently tracked jobs.

## Schema Model

Schemas stored in `document_registry.schema_definition` follow the `RegistrySchema` contract from `src/schemas.py`:

```json
{
  "vendor_name": "LABEL_TECH",
  "version": 1,
  "fields": [
    {
      "key": "invoice_number",
      "type": "str",
      "description": "Invoice identifier"
    }
  ]
}
```

Supported field types currently are:

- `str`
- `float`
- `date`
- `list`

`list` fields are mapped to line-item extraction using the `LineItem` schema.

## Reconciliation Plugin

`src/plugins/supply_chain.py` performs deterministic invoice-to-ERP checks:

- invoice vs purchase order price
- invoice vs goods receipt quantity
- unauthorized item detection
- missing receipt detection

The audit result is added to `audit_report` in the final payload.

If no PO can be derived, reconciliation is skipped and the payload still proceeds to webhook delivery.

## Reliability Features

### Redis pending recovery

The worker uses Redis consumer groups and periodically reclaims pending messages older than 10 minutes with `XAUTOCLAIM`.

This protects the pipeline from jobs being stuck forever when a worker crashes after reading a message but before acknowledging it.

### Database connection pooling

Repositories use a shared `asyncpg` connection pool instead of creating a new connection on each call.

### Webhook failure persistence

If the webhook responds with a non-2xx status or the request fails at the transport layer:

- the error is logged with `job_id`
- the job status becomes `DELIVERY_FAILED`
- the payload remains stored in `processing_jobs.extracted_data`

## Testing

Run tests with:

```bash
pytest
```

Focused examples:

```bash
pytest tests/test_fingerprint.py -q
pytest tests/test_schema_json_schema.py -q
```

## Operational Notes

- The current API has no authentication or authorization layer.
- Place the service behind a trusted network boundary or gateway before exposing it externally.
- Uploaded files are stored on the local filesystem under `data/uploads/`.
- `WEBHOOK_URL` is optional. If unset, the pipeline will skip outbound delivery.
- `output_dir` is created automatically by configuration, though current processing primarily uses `uploads_dir`.

## Known Gaps

- `POST /approve` currently accepts `schema_definition` as a generic `dict` instead of validating it as a strict `RegistrySchema` at the API boundary.
- The health endpoint still opens a direct `asyncpg.connect(...)` instead of reusing the shared pool.
- The compose file includes legacy environment wiring that should be cleaned up.

## Repository Layout

```text
src/
  api/
  core/
  infrastructure/
  plugins/
  worker/
sql/
tests/
data/
```

## License

No license file is currently included in the repository.
