# Ironclad OCR

Ironclad helps an operations team answer a practical question: **do the
documents in this case agree enough to proceed, and what needs a human
decision?** It reads document packets, compares the facts that matter to the
workflow, and presents discrepancies with page-level evidence. A reviewer can
then approve, reject, override with a reason, or request reprocessing.

The current pilot is built around Moroccan import dossiers. It
accepts DUM/MLV, DUA, BAD, bill of lading, freight, and supplier documents as
one case. The earlier invoice workflow remains available for vendor-schema
extraction and purchase-order, receipt, and invoice reconciliation.

## Where it helps

- **Before an import dossier moves forward:** compare declaration references,
  container numbers, weights, and required documents across the packet. A
  conflict becomes a reviewable finding tied to its source pages.
- **When a packet is incomplete or hard to read:** surface missing evidence or
  uncertain extraction for a person to resolve instead of silently accepting
  an apparent match.
- **During review and handoff:** keep the case decision, review action, source
  evidence, and JSON/PDF report together so another operator can see why a
  case was held or cleared.
- **For invoice control:** extract invoices with changing vendor layouts and
  compare them with purchase orders and goods receipts in the legacy
  `invoice_3way` workflow.

The import dossier workflow is a pilot, not a production accuracy claim. Its demo
packets exercise the review flow; they are not a representative benchmark.

## How a case moves through Ironclad

1. An operator uploads several PDFs or one merged PDF as a dossier.
2. Ironclad stores the sources and queues the case for background processing.
3. OCR reads the pages; document classification groups them into segments and
   extraction records facts with page evidence and confidence.
4. Workflow rules compare the facts and produce `READY`, `BLOCKED`, or
   `REVIEW_REQUIRED` findings.
5. A reviewer resolves the case, and the same decision model produces a JSON
   or PDF report.

A processing failure is recorded as `FAILED`; it is never presented as a
business `BLOCKED` decision.

The web interface gives operators a dossier list, case detail and source
evidence, review actions, an administration area for source parties and draft
rules, and a notification inbox. The legacy invoice dashboard remains
separately labeled.

## Architecture

```text
FastAPI -> Postgres/Supabase -> transactional outbox -> Redis Streams
                                                     -> worker
                                                     -> provider adapter
                                                     -> workflow plugin
Next.js frontend -> dossier/review/report APIs
```

The design separates document reading, business rules, and delivery:

- `ClientConfig`: client, workflow, provider profile, enabled modules, and
  ruleset version.
- `WorkflowPlugin`: reusable reconciliation behavior such as
  `morocco_import_dossier`.
- `DocumentIntelligenceProvider`: classification and evidence-backed
  extraction. The default adapter uses local PaddleOCR; an OpenAI-compatible
  adapter remains optional.
- Infrastructure repositories: Postgres, Supabase Storage, Redis, and webhook
  delivery.

The case and its audit event are written with a transactional outbox entry
before work is published to Redis. This lets the worker retry processing
without treating a queue publication failure as a completed case. Client
configuration selects the workflow and provider, while rules stay
deterministic and reviewable.

The Compose stack bundles a CPU/ONNX PaddleOCR service using
`PP-OCRv6_small_det` and `PP-OCRv6_small_rec`. It recognizes PDF text and
returns text, confidence, page, and bounding-box evidence. Deterministic
Import dossier rules classify pages and extract pilot facts; uncertain pages remain
`UNKNOWN` for human review. OpenAI-compatible extraction remains optional via
`DOCUMENT_PROVIDER=openai`.

## Case and Decision States

Case lifecycle:

- `INGESTED`
- `PROCESSING`
- `AWAITING_REVIEW`
- `RESOLVED`
- `FAILED`

Decision status:

- `READY`
- `BLOCKED`
- `REVIEW_REQUIRED`

Review resolution:

- `APPROVED`
- `REJECTED`
- `OVERRIDDEN`

Legacy invoice jobs continue to use `PENDING`, `PROCESSING`,
`WAITING_HUMAN`, `COMPLETED`, `FAILED`, and `DELIVERY_FAILED`.

## API

### Dossiers

- `POST /dossiers`: multipart `files`, `client_id`, and optional
  `external_reference`.
- `GET /dossiers?client_id=<your_client_id>`: list tenant-scoped cases.
- `GET /dossiers/{case_id}?client_id=<your_client_id>`: retrieve the case, documents,
  facts, evidence, decision, and review history.
- `POST /dossiers/{case_id}/reviews`: approve, reject, or override the current
  decision with optimistic version checking and an idempotency key.
- `POST /dossiers/{case_id}/reprocess`: requeue selected source documents.
- `GET /dossiers/{case_id}/report?client_id=<your_client_id>&format=json|pdf`.
- Intake can record its channel and sender provenance for each uploaded source.

### Administration

- `/admin/parties`: manage client-scoped source parties.
- `/admin/rule-sets`: list and create draft rulesets, then activate a confirmed draft.
- `/admin/notifications`: list notifications and mark them read.

The dossier and administration APIs require a Supabase bearer token and an
active `PLATFORM_SUPER_ADMIN` user. The legacy invoice endpoints listed below
do not yet share that authorization boundary; do not expose them publicly.

Cross-client lookups return `404`.

### Legacy invoice workflow

- `POST /ingest`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /approve`
- `GET /health`

## Configuration

Environment is loaded from `.env`.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | none | Postgres/Supabase connection |
| `SUPABASE_URL` | Yes for ingestion | none | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes for ingestion | none | Storage service access |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis Streams |
| `DOCUMENT_PROVIDER` | No | `paddle` | `paddle` or `openai` worker provider |
| `PADDLE_OCR_URL` | Paddle worker | `http://localhost:8080` | PaddleOCR service URL |
| `PADDLE_OCR_MODEL` | No | PP-OCRv6 small | Provider model identifier in reports |
| `PADDLE_OCR_TIMEOUT_S` | No | `300` | PaddleOCR request timeout |
| `LLM_API_KEY` | Cloud provider | empty | Model-provider key |
| `LLM_API_KEY_REQUIRED` | No | `true` | Allow an unauthenticated local endpoint when false |
| `LLM_BASE_URL` | No | provider default | OpenAI-compatible endpoint |
| `MODEL_NAME` | No | `gpt-4o` | Provider model identifier |
| `TEMPERATURE` | No | `0.1` | Model temperature |
| `DRIFT_THRESHOLD` | No | `0.8` | Legacy layout-match threshold |
| `MAX_UPLOAD_MB` | No | `25` | Per-file upload limit |
| `MAX_DOSSIER_FILES` | No | `20` | Files per dossier |
| `MAX_DOSSIER_PAGES` | No | `200` | Total pages per dossier |
| `WEBHOOK_URL` | No | none | Legacy invoice delivery |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

Do not commit `.env` or credentials.

## Database

The migration source of truth is `supabase/migrations/`. It currently contains
seven migrations covering registry jobs, invoice processing, client tenancy,
dossiers, intake provenance, ruleset administration, and notifications.

Migration `006` adds the dossier domain, source/segment artifacts, extraction
evidence, decisions, reviews, audit events, outbox, retry metadata, and
tenant-scoped ERP references. The seventh migration adds source provenance,
client-scoped parties, rule-set administration, and notifications.

The legacy `sql/` directory mirrors the first six migrations for reference.
Check the target project's remote migration history with
`supabase migration list` before applying changes. Create future migrations
through the Supabase CLI.

## Run

Install local development dependencies:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
Set-Location frontend
npm ci
```

Run the complete stack:

```powershell
docker compose up -d --build
```

Services:

- frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Redis
- local PaddleOCR service
- invoice/dossier worker
- transactional outbox dispatcher

The Compose stack still requires reachable Supabase/Postgres credentials in
`.env`.

## Verification

```powershell
python -m pytest -q
python -m compileall -q src tests services/paddle_ocr
Set-Location frontend
npm run lint
npm run build
Set-Location ..
docker compose config --quiet
supabase migration list
```

`demo_dossiers/` contains three seven-document scenario packs for container
number, weight, and declaration-reference mismatches. They are demonstration
copies derived from client source PDFs, with an intentional exception
banner on the modified document in each pack. Treat them as client documents
when sharing the repository. These packs can smoke-test page coverage, workflow
stability, evidence links, and report generation, but they cannot support
extraction-accuracy claims. Formal accuracy evaluation requires 30-50 reviewed
representative dossiers.

## Production Gates

Before a second live client or internet exposure:

- authentication, organizations, and roles
- RLS and private storage with signed URLs
- immutable reviewer identity and stronger audit controls
- backup/restore testing
- metrics, tracing, alerting, and dead-letter operations
- evaluated local/cloud provider profiles
- verified migration history and deployment rollback procedure

## License

The source is available under the [PolyForm Noncommercial License 1.0.0](LICENSE).
For commercial use, [contact the maintainer through GitHub Issues](https://github.com/kourdroid/OCRAgent/issues/new)
to request a separate license. Client-derived PDFs in `demo_dossiers/` are not
licensed for reuse. Third-party dependencies keep their own terms.
