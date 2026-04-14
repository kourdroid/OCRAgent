## Overview
I'm using the planning skill to create the implementation plan.

You already have a working single-process OCR watcher (`main.py` + `src/processor.py`). This plan evolves it into your 4-layer architecture: FastAPI gateway + Redis queue (Docker, latest Redis) + Worker + Supabase registry/jobs + LangGraph state machine + human-in-the-loop.

Sources used (Context7):
- LangGraph: `/langchain-ai/langgraph/1.0.6` and `/websites/langchain_oss_python_langgraph`
- FastAPI: `/fastapi/fastapi/0.115.13`
- Supabase Python: `/supabase/supabase-py`
- Redis Python: `/redis/redis-py/v6_4_0`

## Target Architecture Mapping
- **API**: `POST /ingest` (upload + create job in Supabase + push job to Redis)
- **Worker**: consumes Redis jobs, runs LangGraph pipeline, updates Supabase job state, emits webhook
- **Supabase**:
  - `document_registry`: vendor layout memory (schema_definition + fingerprint_hash + version)
  - `processing_jobs`: job state machine mirror (PENDING/PROCESSING/WAITING_HUMAN/COMPLETED/FAILED)
- **LangGraph**: internal orchestration of steps (identify -> lookup -> drift -> discover/evolve -> human hold -> save -> extract)

## Redis Decision (Per Your Instruction)
- Redis runs via Docker using the **latest Redis image**.
- For safety and reproducibility, we will still **pin to major** in compose (e.g., `redis:7-alpine`) unless you explicitly want `redis:latest`. Either way, the compose file will be the single source of truth.
- Queue primitive: **Redis Streams + consumer groups** (recommended for crash-safety). If you later insist on list+BRPOP, we can swap without changing API contracts.

## Layer 1: Foundation (Infrastructure)
**Goal:** dockerized services and config that can connect to Redis + Supabase.

### Files to add/modify
- Create `Dockerfile` (API/worker image)
- Create `docker-compose.yml`
  - services:
    - `redis`: `image: redis:7-alpine` (or `redis:latest` if you prefer), port 6379, persistence volume
    - `api`: FastAPI container
    - `worker`: async worker container
- Update `.env` structure and add `.env.example`
- Refactor [src/config.py](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/src/config.py)
  - Replace hardcoded values with environment-driven settings
  - Add:
    - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
    - `REDIS_URL` (e.g., `redis://redis:6379/0` in docker)
    - `WEBHOOK_URL`
    - `MODEL_NAME`, `TEMPERATURE`
    - `DRIFT_THRESHOLD` (default 0.8)
    - `POPPLER_BIN` (optional)

### Verification
- Redis ping via `redis.asyncio` (Context7 redis asyncio connect)
- Supabase CRUD smoke test on `processing_jobs` (Context7 supabase insert/select)

## Layer 2: Core Nodes (The Organs)
**Goal:** implement pipeline steps as isolated functions with typed inputs/outputs.

### Files to add/modify
- Modify [src/schemas.py](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/src/schemas.py)
  - Add your blueprinted models:
    - `FieldDefinition`, `RegistrySchema`
  - Keep `Invoice` for legacy path, but introduce dynamic extraction output validation:
    - Build JSON schema from `FieldDefinition[]` and enforce it on Gemini output
- Create `src/core/nodes.py`
  - `identify_vendor(image) -> str | None`
  - `discover_schema(image) -> RegistrySchema`
  - `detect_drift(image, existing_schema) -> tuple[bool, float]`
  - `extract_with_schema(image, schema) -> dict`
  - Helpers:
    - `extract_header_text(image) -> str` (fast prompt to Gemini)
    - `compute_fingerprint(text) -> str` (sha256)

### Defensive behavior requirements
- Catch specific exceptions only at I/O boundaries (LLM, FS, Supabase, Redis)
- Every LLM call: explicit timeout + structured response schema (reuse `get_clean_schema` approach from [src/processor.py](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/src/processor.py))
- Drift detection: header fingerprint + similarity score -> `drift_confidence` -> threshold gate

### Tests (TDD)
- `tests/test_fingerprint.py`
- `tests/test_drift_detection.py`
- `tests/test_schema_json_schema.py`

## Layer 3: The Graph (LangGraph)
**Goal:** wire nodes into a resilient LangGraph StateGraph.

### Files to add/modify
- Create `src/core/state.py`
  - Define `AgentState` as `TypedDict` matching your blueprint (plus `proposed_schema` and `error`)
- Create `src/core/graph.py`
  - Build `StateGraph(AgentState)` (Context7 LangGraph StateGraph snippet)
  - Prefer `Command(goto=..., update=...)` for atomic update+route (Context7 Command examples)
  - Optional conditional edges where clearer
  - Checkpointer:
    - default `InMemorySaver`
    - optional Postgres-based checkpointer if env provided (Context7 PostgresSaver/AsyncPostgresSaver)

### HITL Resume Strategy
- On discovery/evolution:
  - write `proposed_schema` to Supabase
  - set job to `WAITING_HUMAN`
  - stop processing (no further extraction)
- On approval:
  - update registry row
  - set job back to queued state
  - re-push job into Redis stream

### Tests
- `tests/test_graph_routing.py`
- `tests/test_graph_state_updates.py`

## Layer 4: Interface (FastAPI + Worker)

### API
- Create `src/api/app.py`
- Create `src/api/routes.py`
  - `POST /ingest`: create job row -> push to Redis stream -> return `job_id`
  - `POST /approve`: upsert registry -> requeue job in Redis stream

FastAPI endpoint patterns follow Context7 examples (Pydantic request bodies).

### Worker
- Create `src/worker/worker.py`
  - Uses `redis.asyncio` client (Context7 redis asyncio connect)
  - Consumes Redis Streams using consumer groups (ack/retry safe)
  - Updates Supabase job record at each stage (PROCESSING/WAITING_HUMAN/COMPLETED/FAILED)
  - Runs LangGraph with `configurable.thread_id = job_id`

### Tests
- `tests/test_api_ingest.py`
- `tests/test_api_approve.py`

## Dependency Updates
Update `requirements.txt` to include:
- `fastapi`, `uvicorn`
- `redis`
- `supabase`
- `langgraph`
- `pytest`, `pytest-asyncio`, `httpx`

## Database Migration Artifacts
- Add `sql/001_registry_jobs.sql` containing your provided SQL for manual execution in Supabase.

## Acceptance Criteria
- Known layout: registry match -> drift false -> extraction completes quickly
- Unknown/drift layout: proposed schema stored + job WAITING_HUMAN
- Approval: registry updated + job requeued
- Worker crash-safe: jobs not lost (Streams + consumer group)
- All external inputs validated; no hardcoded secrets

## Deliverables Produced By This Implementation Round
- Dockerized API + Worker + Redis (latest Redis in Docker)
- Supabase adapters for registry/jobs
- LangGraph graph and core nodes
- FastAPI endpoints for ingest/approve
- Test suite covering routing + adapter contracts