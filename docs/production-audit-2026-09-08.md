# Ironclad production audit — 8 September 2026

## Verdict

**NO-GO for production.** Ironclad has a useful prototype architecture, but the deployed system is unavailable and several security, correctness, recovery, and auditability defects remain. Restoring the database connection alone would not make it production-ready.

This audit covers the working tree at **D:/Projects/Ironclad-OCR**, including uncommitted and untracked product files, plus the existing local Docker deployment. It is a read-only product audit: no application fixes, migrations, restarts, customer uploads, rule activations, or approvals were performed.

The existing Compose containers were created from the older C: checkout according to their labels. The dossier processor SHA-256 was compared with the D: source and matches. That proves equivalence for that file only, not the entire deployed image. Source findings and deployment findings are therefore identified separately.

There is no defensible single “percentage ready.” Authentication, correct decisions, recoverable processing, and private documents are release gates; a good score elsewhere cannot compensate for a failure in one.

## Evidence and limits

- Existing backend suite: **52 passed in 5.31 seconds** on the host Python 3.13 environment.
- Compose configuration validates.
- Live API health: HTTP 200 with body status **degraded**; Redis healthy, PostgreSQL connection rejected with a tenant/user-not-found error.
- API unhealthy; worker and outbox repeatedly restarting; frontend, Redis, and Paddle health checks green.
- Unauthenticated GET /dossiers and /admin/rule-sets return **401**.
- Unauthenticated GET /jobs reaches the database and returns **502**, rather than an authentication rejection.
- Browser at /dossiers renders a French sign-in page. No authenticated session was available; authenticated end-to-end processing was not verified. The previous loading-screen observation was not reproduced.
- Redis accepts an unauthenticated host connection. Its runtime configuration has protected-mode=no, wildcard bind, appendonly=no, and scheduled RDB snapshots.
- Seven isolated probes reproduce rule serialization, insufficient-evidence matching, invalid required-document configuration, demo-specific extraction, missing decision recovery on redelivery, missing legacy route authentication, and PDF comment parsing defects. Run: `python docs/audit_probes_2026_09_08.py`.
- Frontend dependency scan: **14 affected package entries: 9 high, 3 moderate, 2 low**. Full scanner output: [audit-npm-2026-09-08.json](D:/Projects/Ironclad-OCR/docs/audit-npm-2026-09-08.json).
- Direct pinned backend dependency scan: **6 known advisories in pypdf 6.14.2**.
- Direct pinned OCR-service dependency scan: **no known advisories reported**. This is not a clean bill of health for transitive dependencies, native libraries, models, or container operating systems.
- Original frontend node_modules is incomplete. Standard commands cannot locate eslint/next; direct entrypoints fail on missing Next internals. A separate temporary copy with a clean npm install was used for build/lint verification; final results appear in the verification addendum.
- Database contents, actual deployed RLS/grants, bucket visibility, backup settings, external firewall/TLS, real user roles, and restoration were not verified because the database is unavailable and no production hosting scope was supplied.
- No destructive stress tests, malicious-PDF execution, real data exfiltration, credential changes, or external writes were performed.

## Coverage from A to Z

| Area | Assessment | Main evidence or gap |
|---|---|---|
| A — Availability | Fail | Database rejected; API unhealthy; workers restarting. |
| B — Builds and release provenance | Incomplete | Dirty tree, old container origin, broken local dependencies; isolated build checked separately. |
| C — Credentials and authentication | Fail | Dossier/admin routes protected; legacy routes open. |
| D — Data isolation | Fail for multi-client production | Only platform-super-admin role; legacy job listing can span clients. |
| E — Encryption and document privacy | Fail in design / deployment partly unknown | Public object URL contract; external TLS and bucket setting unverified. |
| F — File intake | Partial | PDF signature/size/page checks exist, but full reads and expensive parsing precede effective resource isolation. |
| G — General OCR accuracy | Unproven | Real OCR, but extraction contains literal demo values; no representative benchmark. |
| H — Human review | Partial | Version checks and explicit override exist; reviewer identity is not persisted. |
| I — Idempotency | Partial | Job/outbox keys exist; intake retry does not return original result, UI regenerates review keys. |
| J — Job recovery | Fail | Decision completion gap and historical-failed-job reprocessing defect. |
| K — Known dependency advisories | Fail gate | npm and pypdf findings require patching and reachability review. |
| L — Logging and monitoring | Partial | Structured log messages; no end-to-end progress alert or demonstrated operations dashboard. |
| M — Migrations | Unverified in deployment | Seven migration files; no successful current migration-state readback. |
| N — Network boundaries | Fail | Redis published on all interfaces without authentication; API unrestricted CORS. |
| O — Outbox durability | Partial | Transactional outbox exists; Redis loss after publication lacks automatic reconciliation. |
| P — Performance and capacity | Unproven / known risks | Serial OCR, overlapping polling, nested DB pool acquisition, no load envelope. |
| Q — Quality assurance | Insufficient | Existing tests pass but miss reproduced production defects; no full authenticated E2E proof. |
| R — Rule semantics | Fail | JSON decode bug, missing type validation, insufficient evidence accepted, no numeric/date implementation. |
| S — Source evidence | Partial | Page/text/confidence/bbox stored; bbox not highlighted; downloaded bytes not checked against stored hash. |
| T — Tenant/provider architecture | Partial | Useful plugin interfaces; concrete repository and global provider routing. |
| U — UX and accessibility | Fail for independent operator use | Raw codes, mixed languages/themes, no guided rule editing/testing, source-level keyboard/label gaps. |
| V — Versioned decisions and reports | Partial | Decision versions exist; report can mix old decision with current documents after reprocessing. |
| W — Webhooks and legacy workflow | Partial | Failure recorded, but no durable delivery retry; legacy state is in-memory. |
| X — Exception handling | Partial | Some clear errors; storage HTTP failures can fail entire dossier, admin errors can misreport DB failures. |
| Y — Recovery, retention, and support | Unproven | No demonstrated restore, retention enforcement, deletion workflow, or incident rehearsal. |
| Z — Operational acceptance | Fail | No stable deployed E2E, measured OCR acceptance, or release gate enforcement. |

## Findings that block release

Priority meanings: **P0** = remove before exposing the system to untrusted networks/users; **P1** = production blocker; **P2** = important operational/usability improvement. “Source-confirmed” means the behavior follows the inspected code; it does not claim a successful live database reproduction.

### F01 — P0: Legacy endpoints bypass authentication

**Confirmed by source and route dependency inspection.** /ingest, /jobs, /jobs/{job_id}, and /approve have no authentication dependency. The frontend AuthGate does not protect these APIs. /jobs accepts no client filter and the repository can return jobs across clients, including dossier jobs stored in the same table. /approve changes the learned schema and requeues work.

Live anonymous /jobs reached the database (502 during the outage); dossier/admin equivalents returned 401. No live write was attempted.

**Impact:** once the database recovers, reachable legacy routes can expose data or accept unauthorized processing/schema changes. Fix by applying server-side identity and authorization consistently or removing legacy routes from the production application.

**Acceptance:** anonymous requests rejected; user A cannot list/read/change user B's client data; legacy mutation endpoints covered by authorization tests.

Evidence: [routes.py](D:/Projects/Ironclad-OCR/src/api/routes.py:26), [app.py](D:/Projects/Ironclad-OCR/src/api/app.py:24).

### F02 — P0: Redis is reachable without authentication

**Live-confirmed.** Compose publishes 6379 on IPv4 and IPv6 wildcard interfaces. Host PING without a password succeeds. Runtime protected mode is disabled. External reachability still depends on the host firewall; internet exposure was not tested.

**Impact:** anyone with network access to that port may read or alter queue state. Queue payload file paths are trusted by the worker and can point to arbitrary HTTP URLs or local paths; this widens the impact of queue compromise. No queue write or exploit was attempted.

**Acceptance:** remove the host port unless needed; otherwise bind only an explicitly approved interface and enforce ACLs/network restrictions. Resolve job inputs from trusted database records and restrict file retrieval.

Evidence: [docker-compose.yml](D:/Projects/Ironclad-OCR/docker-compose.yml:2), [processor.py](D:/Projects/Ironclad-OCR/src/dossiers/processor.py:85).

### F03 — P1: The current system cannot process production work

**Live-confirmed.** PostgreSQL rejects the configured tenant/user; the API is unhealthy and worker/outbox restart. Redis/Paddle/frontend being green does not mean the workflow works.

**Acceptance:** correct the deployed connection configuration, verify required migrations, and complete an authenticated upload → OCR → decision → review → report run after a cold start. Record sustained health and actual queue progress.

### F04 — P1: Database ruleset deserialization is broken

**Locally reproduced.** list_rulesets selects jsonb_agg(...) AS rules. _serialize_row decodes several JSON fields but omits rules. No custom JSON codec is installed in the connection pool. With the standard asyncpg string representation, evaluate_ruleset iterates characters and raises **AttributeError: 'str' object has no attribute 'get'**. The UI's rules.length can also report a string length instead of a rule count.

asyncpg's documented default for json/jsonb is str. [Official asyncpg type mapping](https://github.com/MagicStack/asyncpg/blob/master/docs/usage.rst).

**Acceptance:** decode/validate a typed ruleset at the repository boundary; test a real PostgreSQL read, API response shape, and subsequent evaluation.

Evidence: [dossier_repos.py](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:36), [list_rulesets](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:128).

### F05 — P1: A crash can strand a fully extracted dossier without a decision

**Source-confirmed; redelivery behavior reproduced.** save_source_results commits COMPLETED for a source/job before the processor checks dossier readiness or saves a decision. If the process dies in that interval, redelivery sees COMPLETED and returns immediately. The probe shows zero readiness checks and zero decision saves for a completed source.

**Impact:** all files may look processed while the dossier never receives its final decision. Explicitly caught transient exceptions have a retry path; abrupt process death does not.

**Acceptance:** make finalization separately durable/idempotent, or resume decision completion for completed jobs. Inject a crash after the last source commit and demonstrate recovery without manual reprocessing.

Evidence: [processor.py](D:/Projects/Ironclad-OCR/src/dossiers/processor.py:120), [save_source_results](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:509).

### F06 — P1: Reprocessing cannot clear historical failed jobs

**Source-confirmed; live database reproduction unavailable.** reprocess_sources creates new jobs without superseding old FAILED jobs. is_case_ready_for_decision counts every job for the case where status differs from COMPLETED. Historical failures therefore keep readiness false even if every replacement job succeeds.

**Acceptance:** introduce processing generations or an explicit active-job/superseded model; readiness must consider only the intended run. Test failure → reprocess → successful decision.

Evidence: [readiness query](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:660), [reprocess_sources](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:1258).

### F07 — P1: Equality and required-field rules can hide missing evidence

**Locally reproduced.** EXACT_MATCH succeeds whenever the set of nonempty normalized values has length one. One low-confidence value and an entirely missing counterpart produce zero discrepancies. Source document selectors are not enforced; FIELD_REQUIRED can pass if a value exists anywhere.

The overall decision still remains REVIEW_REQUIRED, so this is **not an automatic approval exploit**. It is a misleading rule result: the reviewer is not shown the missing comparison.

**Acceptance:** explicit document scope, minimum source cardinality, evidence/confidence requirements, and separate PASS/FAIL/NOT_APPLICABLE/REVIEW_REQUIRED outcomes.

Evidence: [rules.py](D:/Projects/Ironclad-OCR/src/dossiers/rules.py:59).

### F08 — P1: Rule creation accepts configurations the evaluator cannot execute

**Locally reproduced.** The UI sends field_path for REQUIRED_DOCUMENT; the evaluator requires parameters.document_type. A present DUM_MLV is reported as “Required document type unknown is missing.” Authority fields are top-level in the request model but read from parameters by the evaluator. Numeric/date templates are accepted by the API but always fall into a generic review branch. Empty rule sets can be activated.

**Acceptance:** discriminated, template-specific validated inputs; activation rejects incomplete/unsupported/empty configurations. UI controls must match that contract.

Evidence: [models.py](D:/Projects/Ironclad-OCR/src/dossiers/models.py:212), [admin/page.tsx](D:/Projects/Ironclad-OCR/frontend/src/app/admin/page.tsx:63), [activate_ruleset](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:184).

### F09 — P1: Activating rules changes safety behavior and normalization

**Source-confirmed.** Active rules replace workflow.reconcile rather than supplement it. The active evaluator does not reproduce the fallback's explicit unknown-document, missing-fact, and low-confidence discrepancies. Normalization also changes: fallback strips identifier punctuation and B/L leading zeros; active rules remove whitespace only. An activation can create new false mismatches and remove useful warnings.

Without active rules, the current code still runs fallback reconciliation and then forces REVIEW_REQUIRED/UNCONFIRMED. Therefore documents **can be compared by built-in code even when no configurable rules are active**. The proposed September 4 plan is not the current implementation.

**Acceptance:** always-on technical safeguards plus business rules; one documented normalization policy; before/after activation tests.

Evidence: [processor.py](D:/Projects/Ironclad-OCR/src/dossiers/processor.py:200), [rules.py](D:/Projects/Ironclad-OCR/src/dossiers/rules.py:17), [morocco_import.py](D:/Projects/Ironclad-OCR/src/plugins/morocco_import.py:103).

### F10 — P1: Normal approval is unreachable in the dossier workflow

**Source-confirmed.** The active evaluator always returns REVIEW_REQUIRED unless blocked. The default workflow disables automatic readiness, and the no-rules path forces review. resolve_review permits APPROVE only for READY. In normal operation the user must override even a clean case.

Conservative review is a valid pilot policy, but the UI and product claims must explain it. Do not simply enable READY until F07–F09 are fixed.

**Acceptance:** explicit agreed readiness policy and a tested clean dossier → ordinary approval path, or a clearly named manual-approval workflow that does not mislabel routine work as an exception.

Evidence: [rules.py](D:/Projects/Ironclad-OCR/src/dossiers/rules.py:119), [resolve_review](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:1154).

### F11 — P1: Extraction is fitted to demonstration data

**Locally reproduced.** The bill-of-lading extractor recognizes container 767208 but extracts nothing for MSCU1234567 using otherwise equivalent OCR input. Other rules contain WASA EXPRESS, ONDUPET, DUROC, specific goods values and quantities, and a declaration-year prefix. These are real regex constraints, not a general learned extraction system.

The service performs real OCR; the weakness is how OCR text becomes business fields. A successful known fixture does not establish unseen-document accuracy.

**Acceptance:** remove literal business values, evaluate representative unseen documents, report per-field correctness/missing-value rates, and route ambiguity to review.

Evidence: [paddle_document_provider.py](D:/Projects/Ironclad-OCR/src/infrastructure/paddle_document_provider.py:225).

### F12 — P1: Multiple candidate values are silently collapsed

**Source-confirmed.** _extract_facts keeps the first matching fact for each field, skipping later candidates. Multi-container or contradictory documents can lose information before reconciliation. Classification confidence is calculated from marker counts, not calibrated accuracy, and equal high marker scores are not handled as ambiguity. Adjacent pages of the same type are merged into one segment.

**Acceptance:** support repeated fields/documents or explicitly reject them into review; retain alternatives and benchmark segmentation/classification confidence.

Evidence: [classification](D:/Projects/Ironclad-OCR/src/infrastructure/paddle_document_provider.py:65), [extraction](D:/Projects/Ironclad-OCR/src/infrastructure/paddle_document_provider.py:348).

### F13 — P1: Document access depends on public URLs

**Source-confirmed; actual bucket public/private setting unverified.** upload returns /storage/v1/object/public/...; the worker fetches without storage authentication, and the browser embeds the same URL. A public bucket exposes files to URL holders; a private bucket breaks this access contract.

**Acceptance:** private storage with authorized document delivery, scoped short-lived URLs where appropriate, tenant checks, and anonymous-download denial tests. Do not infer safety from unguessable UUIDs.

Evidence: [supabase_storage.py](D:/Projects/Ironclad-OCR/src/infrastructure/supabase_storage.py:65), [processor.py](D:/Projects/Ironclad-OCR/src/dossiers/processor.py:85), [review page](D:/Projects/Ironclad-OCR/frontend/src/app/dossiers/[id]/page.tsx:247).

### F14 — P1: Reviewer identity and complete rule outcomes are absent

**Source-confirmed.** Authentication checks the user, but review_dossier does not pass that identity into resolve_review. Review/audit rows record resolution and comment without an actor. rule_evaluation_results exists in SQL but has no application writes. Only discrepancies are stored, so a report cannot enumerate all controls that passed or were skipped.

**Acceptance:** persist immutable actor identity and per-rule results with decision version, evidence, reason, and timestamp. Protect audit records against ordinary mutation. Authentication alone is not an audit trail.

Evidence: [review_dossier](D:/Projects/Ironclad-OCR/src/api/dossier_routes.py:299), [resolve_review](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:1154), [migration](D:/Projects/Ironclad-OCR/supabase/migrations/20260813210527_delassus_intake_rules_notifications.sql:108).

### F15 — P1: Reports can combine different processing versions

**Source-confirmed.** get_case loads current active documents and the latest existing decision independently. Reprocessing keeps the old decision while replacing active extracted segments. Report generation accepts any existing decision, even while the case is PROCESSING. The result can pair old conclusions with new evidence. Reads also are not one consistent database snapshot.

**Acceptance:** bind report documents/evidence to an immutable processing/decision version; block or clearly label reports during reruns; test report consistency under concurrent processing.

Evidence: [get_case](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:1083), [build_canonical_report](D:/Projects/Ironclad-OCR/src/dossiers/reporting.py:22).

### F16 — P1: A normal comment can break PDF generation

**Locally reproduced.** A review comment containing “Literal <b>text” causes ReportLab to raise ValueError because text is inserted into Paragraph without XML escaping. Other interpolated strings use the same unsafe helper. Tables also use plain strings with fixed widths, creating overflow risk for long OCR evidence.

**Acceptance:** escape user/document text before markup parsing; test angle brackets, ampersands, long evidence, Unicode, and multi-page reports. No external image/network markup exploit was attempted.

Evidence: [reporting.py](D:/Projects/Ironclad-OCR/src/dossiers/reporting.py:37), [review rendering](D:/Projects/Ironclad-OCR/src/dossiers/reporting.py:166).

### F17 — P1: Redis loss can strand published work

**Live configuration plus source-confirmed design gap.** Redis uses scheduled snapshots with AOF disabled. After the outbox marks an event PUBLISHED, the dispatcher does not revisit it. If Redis loses a recently published entry, the database job can remain pending without a queue message. XAUTOCLAIM only recovers entries still present in Redis.

Redis documents the durability difference between snapshots and append-only logging. [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

**Acceptance:** define recovery-point requirements, configure appropriate persistence, and add reconciliation from database jobs to transport. Demonstrate recovery after queue data loss in an isolated environment.

Evidence: [outbox_dispatcher.py](D:/Projects/Ironclad-OCR/src/worker/outbox_dispatcher.py:26), [claim_outbox_events](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:380).

### F18 — P1: Concurrent requests can exhaust the DB pool

**Source-confirmed risk; not load-reproduced against the unavailable DB.** get_case holds one pooled connection and calls load_case_context, which acquires a second connection. With max_size=10, ten overlapping detail requests can each retain one connection while waiting for another. There is no acquisition timeout here. Frontend polling makes overlap plausible.

**Acceptance:** reuse one connection or release before nested acquisition; bound timeouts and load-test concurrent detail/report requests.

Evidence: [get_case](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:1083), [load_case_context](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:676), [pool](D:/Projects/Ironclad-OCR/src/infrastructure/supabase_repos.py:30).

### F19 — P1: Retry/idempotency contracts are incomplete

**Source-confirmed.** Intake accepts an idempotency key but uploads files and inserts a new case before a duplicate-key conflict; it does not retrieve the original successful response. Reprocessing has no caller idempotency key. Review UI generates a fresh key per attempt. Concurrent ruleset creation uses MAX(version)+1 without serialized allocation; simultaneous calls can conflict and create_ruleset can return the latest row rather than its own row.

**Acceptance:** stable operation keys, payload consistency checks, return of original outcomes, and concurrent duplicate-request tests.

Evidence: [ingest_dossier](D:/Projects/Ironclad-OCR/src/api/dossier_routes.py:114), [create_ruleset](D:/Projects/Ironclad-OCR/src/infrastructure/dossier_repos.py:150), [review page](D:/Projects/Ironclad-OCR/frontend/src/app/dossiers/[id]/page.tsx:88).

### F20 — P1: Dependency and resource-safety gates fail

The frontend lockfile audit reports 14 affected entries. Some are tooling/transitive paths; the report does not assert they all execute in the deployed server. For example, the cited Next.js Server Action advisory requires a Server Action, and none was found in frontend/src. Its installed version is still in the affected range. [Next.js advisory and applicability](https://github.com/vercel/next.js/security/advisories/GHSA-m99w-x7hq-7vfj).

The pinned pypdf 6.14.2 has six scanner advisories, including excessive runtime/memory consumption. [pypdf parsing advisory](https://github.com/py-pdf/pypdf/security/advisories/GHSA-fc8x-2rww-xw9m). Scanner output indicates fixes up through 6.16.1 for the reported set; retest after selecting patched versions.

Dossier intake reads an entire file before checking its size and parses PDFs on the API event loop. Legacy intake lacks the dossier's size/page controls. OCR renders pages without a maximum pixel-area guard and serializes inference behind one lock. No explicit CPU/memory limits or request-rate limits are supplied in Compose.

**Acceptance:** patch and assess dependency reachability, scan resolved/container dependencies, enforce streaming byte/page/pixel/time limits, and measure safe concurrency using isolated synthetic workloads.

## Further important findings

### F21 — P1: Production authorization is only “platform super-admin”

The app_users constraint permits only PLATFORM_SUPER_ADMIN; all dossier and admin routes require it. There is no operator/reviewer/client-admin separation or user-to-tenant membership boundary. RLS is enabled for newer tables in the migration, but no tenant policies are supplied there, and backend direct PostgreSQL access uses the configured privileged connection. Older processing/registry/ERP tables do not receive RLS in those inspected migrations.

This does not prove deployed anonymous database exposure: actual grants/policies could differ and are unverified. It does establish that multi-client least-privilege access is not implemented as an application feature.

**Acceptance:** explicit permissions, tenant membership, DB/storage isolation tests, and reviewer/admin separation.

### F22 — P2: Rule administration is not usable as a business tool

The interface asks for raw field paths and enum codes, creates one rule per new ruleset, hardcodes warning/REVIEW_REQUIRED, lacks editing a full draft, preview, test-before-activation, and document-scoped comparison controls. It displays “tested rule templates” without executing a user-facing test.

**Acceptance:** guided French rule builder with compatible field/document choices, consequences, examples, plain-language preview, draft editing/versioning, and sample-dossier results.

Evidence: [admin page](D:/Projects/Ironclad-OCR/frontend/src/app/admin/page.tsx:13).

### F23 — P2: Dossier UX hides the operator's next step

Source inspection shows mixed French/English, raw lifecycle/decision codes, dark administration versus light dossier pages, weak labels on inputs/selects, and clickable table rows without keyboard link semantics. Only the first 100 dossiers are fetched and filtering is client-side; older dossiers can disappear from ordinary navigation. Evidence navigation changes the PDF page but never highlights its bbox. Unknown sender/issuer warnings are stored, but that provenance is not passed into the decision context as a rule safeguard.

The sign-in screen was inspected visually; authenticated layout, mobile behavior, and screen-reader flows remain unverified.

**Acceptance:** novice user walkthrough of upload, rule creation, discrepancy review, evidence inspection, decision, and report; keyboard and responsive checks; pagination/search and explicit processing/error states.

Evidence: [dossier list](D:/Projects/Ironclad-OCR/frontend/src/app/dossiers/page.tsx:39), [useDossiers](D:/Projects/Ironclad-OCR/frontend/src/hooks/use-dossiers.ts:22).

### F24 — P2: Polling and session requests have no bounded recovery

AuthGate.getSession has no rejection/timeout handling; API requests have no abort deadline; setInterval can start a new detail/list request while the previous request is still pending and continues after terminal states. The current login renders, but the source risk remains. Report-download errors are launched with void and have no visible catch in the page.

**Acceptance:** cancellation/timeouts, serialized adaptive polling that stops at terminal states, actionable session/API failures, and visible download errors.

Evidence: [auth-gate](D:/Projects/Ironclad-OCR/frontend/src/components/auth-gate.tsx:28), [api client](D:/Projects/Ironclad-OCR/frontend/src/lib/api.ts:36), [detail polling](D:/Projects/Ironclad-OCR/frontend/src/hooks/use-dossier.ts:39).

### F25 — P1: Observability and operational recovery are not demonstrated

/health returns 200 when degraded and exposes raw database errors. Worker health checks verify dependencies, not that the loop is progressing. Outbox gives up after ten publish failures but no operator retry/alert path is supplied. Redis streams are acknowledged but never trimmed; no retention policy is implemented for audit/evidence/source data. One failed source marks all unfinished case jobs failed, increasing retry scope. Storage HTTP failures are not explicitly included in the dossier worker's transient-error tuple.

Backups, restore, deletion/retention, incidents, queue repair, and release rollback are listed as future production gates in README, not demonstrated procedures.

**Acceptance:** measurable health/readiness, stale-job and outbox alerts, safe replay, bounded retention, documented RPO/RTO, and a completed restoration drill.

### F26 — P1: There is no reproducible production release acceptance

The checked-out HEAD is a May commit and substantial product code/migrations are untracked or modified. The running containers originate from another checkout. A normal git checkout of HEAD will not contain this whole product. No CI pipeline was found in the root repository. Host tests are not the Docker Python 3.11 runtime. Python transitive dependencies are not fully locked/hashes supplied. Frontend has npm and pnpm lockfiles while Docker uses npm.

Docker copies the whole backend build context; .dockerignore excludes data/ but does not exclude inbox/, processed/, output/, infos/, demo_dossiers/, or .kilo/. Files in those directories can be baked into images. This audit found a PDF under those non-excluded operational folders, but did not inspect or claim its sensitivity.

**Acceptance:** reviewed committed release, narrow build context, one lockfile policy, immutable image identification, CI backend/frontend/integration tests, migration verification, and rollback rehearsal.

## Architecture assessment

Keep the core direction. A rewrite is not justified by this audit.

Useful foundations already exist:

- source/segment/extraction/evidence/decision/review entities;
- transactional creation of dossier records, jobs, and outbox entries;
- transactional source persistence and decision version locking;
- bounded provider retries and persisted retry scheduling;
- pending Redis message recovery;
- client/workflow interfaces;
- page coverage validation, type validation, and evidence fields;
- a canonical report data model;
- non-root application containers.

However, these pieces do not yet form a fully reliable workflow. Completion, rerun generations, identity, and private document delivery need explicit end-to-end contracts.

The newer dossier path uses DossierProcessor directly; LangGraph orchestrates the legacy path only. InMemorySaver is not durable orchestration storage. Provider selection is global per worker; client provider_profile/ruleset_version metadata is not the runtime selector. The repository is tightly coupled to PostgreSQL and large enough to concentrate several responsibilities. These are manageable design constraints, but claims of fully pluggable per-client orchestration or fully hexagonal architecture would overstate the implementation.

For the optional cloud provider, schema/type validation exists, but returned source text and confidence are model assertions; there is no independent check that each cited value exists in the source PDF. Its healthcheck returns ok without contacting the endpoint. Changing providers requires a documented data-routing policy and a benchmark, not just a configuration switch.

The legacy webhook path records delivery failure but acknowledges the queue message; it lacks a separate durable delivery/retry operation. Legacy database changes and queue publication are not covered by the dossier outbox.

## What must be fixed first

1. **Contain access:** protect/remove legacy routes; isolate/authenticate Redis; implement private document delivery.
2. **Restore the deployment:** valid DB connection, verified migrations, stable API/worker/outbox and a known source/image revision.
3. **Repair correctness and recovery:** ruleset decoding; typed rule contracts; evidence requirements; always-on safeguards; processing generations; crash-safe decision finalization; DB pool nesting.
4. **Make decisions accountable:** reviewer identity, immutable decision evidence, per-rule results, safe consistent reports.
5. **Replace demo extraction:** general patterns/structured candidates and a reviewed unseen-document benchmark.
6. **Finish the operator product:** guided rules, clear readiness policy, French statuses, highlighted evidence, recoverable errors, pagination and accessible interactions.
7. **Prove operations:** patched dependencies, CI/integration/E2E tests, bounded workloads, alerts, restoration, rollback, and a pilot acceptance record.

Do not schedule production by the earlier 6–9-day presentation estimate. That estimate covered a controlled demo, and this audit adds crash recovery, serialization, report consistency, resource safety, and security findings. Estimate implementation after scoping these findings and restoring a test database.

## Release acceptance checklist

Production approval requires evidence for all of these, not merely a green unit test command:

- Authenticated clean, mismatch, missing-document, low-confidence, and failed-processing journeys complete.
- Anonymous and cross-tenant API/storage attempts are denied.
- Every rule result explains inputs, evidence, outcome, and ruleset version.
- Normal approval and override policies are explicit; actor identity is immutable.
- Crash after extraction commit recovers the final decision.
- Failed case reprocessing completes a new run without historical jobs blocking it.
- Duplicate upload/review/reprocess requests return one consistent outcome.
- Reports contain evidence from their exact decision generation and render arbitrary ordinary text safely.
- Representative OCR evaluation meets thresholds agreed for business-critical fields; false negatives and review rates are reported.
- Concurrent detail/report requests do not exhaust the pool; OCR workload fits the measured host capacity.
- Queue loss, outbox failure, and provider outage recover with visible alerts.
- A backup is restored successfully and a release rollback is rehearsed.
- Fresh backend/frontend builds, dependency gates, DB integration tests, and browser E2E checks pass for the release artifact.

## Verification addendum

- Clean installation: npm ci --ignore-scripts --no-audit --no-fund succeeded in an isolated temporary copy (631 packages).
- Frontend lint: **passed**, exit 0.
- Frontend production build: **passed**, exit 0; Next.js 16.2.9 compiled, TypeScript completed, and 14 static pages generated. This ran on host Node 24.16.0, not the Docker Node 22 image, and without production environment secrets; it does not verify authenticated runtime configuration.
- Python compileall for src, tests, and services/paddle_ocr: **passed**.
- Existing backend pytest suite: **52 passed**.
- Audit probes: completed; reproduced the defects described above. Probe success means reproduction worked, not that the application is correct.
- Original checkout dependencies: still incomplete; unchanged by the audit.
- Live deployment remains unhealthy; no authenticated end-to-end upload/review/report was claimed.

Temporary build copy: C:/Users/Mehdi/AppData/Local/Temp/ironclad-audit-build-448a4f1243f34e4da95ccd6173c8b053. It contains copied frontend source and installed dependencies, not copied environment files. It was retained for reproducibility.

## Related artifacts

- [Executable isolated probes](D:/Projects/Ironclad-OCR/docs/audit_probes_2026_09_08.py)
- [Frontend dependency audit](D:/Projects/Ironclad-OCR/docs/audit-npm-2026-09-08.json)
- [Earlier presentation audit](D:/Projects/Ironclad-OCR/docs/delassus-presentation-readiness-audit-2026-09-04.md)
- [Earlier presentation plan](D:/Projects/Ironclad-OCR/docs/delassus-presentation-recovery-plan-2026-09-04.md)

The earlier plan remains useful context, but it is not evidence that its proposed changes were implemented.
