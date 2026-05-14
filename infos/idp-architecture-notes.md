# Ironclad IDP Architecture Notes

This document captures the architecture decisions, concerns, and product direction discussed before implementing the 3-way matching plugin/core refactor. It is meant to guide future engineers and agents so the system evolves as a modular IDP platform instead of a collection of client-specific conditionals.

## Product Understanding

The core product is not OCR itself. OCR, LLM extraction, and model providers are replaceable capabilities around the product, not the product boundary.

The durable value is the decision pipeline:

1. Ingest documents and supporting data.
2. Normalize chaotic inputs into structured facts.
3. Validate those facts against client policy.
4. Match them against selected sources of truth.
5. Produce an auditable decision.
6. Notify or deliver the result through the client's chosen channel.

This means Ironclad should be treated as a headless IDP decision engine with optional interfaces and adapters, not as a single web dashboard or an OCR-only tool.

## Architecture Direction

The system should continue moving toward hexagonal architecture because the domain is client-specific and chaotic. Clients can differ in intake channels, storage constraints, model providers, source-of-truth systems, notification needs, and validation rules.

The core must stay stable while the edges change. These should be adapters around the core:

- Web dashboard
- WhatsApp notifications
- Email and SMTP
- Gmail or IMAP inbox intake
- Webhooks
- Folder watchers
- Supabase, S3, local filesystem, or client-hosted storage
- ERP systems such as Odoo, SAP, or custom databases
- Cloud LLMs, OpenAI-compatible endpoints, local models, or client-hosted model endpoints

The target product shape is a headless IDP core with configurable modules. A client may use the dashboard, another may only receive WhatsApp alerts, and another may require local-only processing. The core should not care which interface or delivery channel is selected.

## Target Layers

The intended layering is:

```text
core/
  Workflow, contracts, domain models, and stable decision language.

adapters/
  Storage, queues, APIs, email, folders, ERP/source systems, and model providers.

plugins/
  Reusable matching and validation logic, such as 3-way matching or folder-to-folder matching.

clients/
  Per-client wiring, selected modules, thresholds, channels, source configuration, and deployment profile.
```

The `clients/` layer is important because client-specific knowledge should not leak into `core/` or force reusable plugins to become one-off client plugins. For example, `supply_chain_3_way` should stay generic, while `clients/label_tech` should decide which sources, tolerances, and notification channels are used for Label Tech.

## Current State Versus Target State

Current state:

- The repo already has a useful pipeline: ingest, split, vendor identification, schema discovery, extraction, reconciliation, persistence, and webhook delivery.
- The backend has clear folders for API, core, infrastructure, worker, and plugins.
- The current 3-way matching logic lives in `src/plugins/supply_chain.py`.
- The graph still directly owns PO lookup, missing-PO behavior, audit shaping, and when the matching function is called.
- Source-of-truth access is tied to current repository methods for Postgres ERP tables.
- The frontend expects `audit_report` and `processing_notification` in `extracted_data`.

Target state:

- The graph invokes a plugin runner instead of directly invoking 3-way matching.
- Matching plugins receive a stable `MatchContext` and return a stable `MatchResult`.
- The plugin decides domain meaning, including whether human review is required.
- The core routes, persists, and delivers results, but does not invent client-specific policy.
- Source-of-truth selection becomes explicit and adapter-based over time.
- Client configuration selects plugins, source adapters, channels, thresholds, and deployment profile.

## Plugin Decisions

The matching boundary needs formal contracts before adding more client plugins.

Required contracts:

- `MatchContext`: the normalized input to a matching plugin. It should include job metadata, vendor/client metadata, extracted document data, source records, and plugin/client config.
- `MatchResult`: the normalized output from a matching plugin. It should include status, discrepancies, confidence, notifications, audit trail, and `requires_human`.
- `Discrepancy`: a structured audit finding with type, severity, message, location, evidence, and anomaly details.
- `AuditEntry`: a traceable explanation of what the plugin checked or decided.
- `SourceQuery` and `SourceRecord`: the stable language for fetching and passing source-of-truth data.

The `requires_human` decision belongs to the plugin, not the core graph. A 2% variance may be acceptable in one domain but critical in another. The plugin knows its domain rules; the core should persist and route the decision without reinterpreting it.

The existing 3-way matching should become the first real plugin. It should not remain an ad-hoc function called directly by the graph.

## Source-Of-Truth Decisions

Source of truth must be explicit. The first milestone should use the current ERP Postgres tables for purchase order and goods receipt data because that is the fastest path to a production-ready 3-way plugin.

Future source adapters may include:

- Postgres or Supabase tables
- Odoo
- SAP
- Uploaded Excel or CSV files
- Watched folders
- Gmail or IMAP inboxes
- SMTP-fed workflows
- Redis-cached ERP snapshots
- Webhook-fed cache tables
- Client-hosted databases
- Local servers in on-prem deployments

The plugin should eventually request normalized `SourceRecord` objects and not care whether they came from Postgres, Excel, Odoo, or a client server.

## Interface And Channel Decisions

The interface is also an adapter.

A client may want:

- A full web validation dashboard.
- No dashboard, only WhatsApp notification on discrepancy.
- Email-based approval.
- Webhook delivery into their ERP.
- Folder output with JSON, PDF, or CSV artifacts.
- Fully automatic processing with no human interface unless a plugin flags `requires_human`.

Interface choice should be client/module configuration. It should not be hardcoded in the IDP core.

For the current milestone, the existing frontend stays stable. `requires_human` should be stored inside `audit_report`, but no new job status or UI flow is required yet.

## Deployment And Privacy Concerns

The product should support multiple deployment profiles over time:

- Shared cloud
- Single-tenant cloud
- Customer VPC
- On-prem
- Local-only or air-gapped

Sensitive clients may require:

- Storage on their own server.
- No external document upload.
- No external model API.
- Private model endpoints or local models.
- SMTP or internal messaging instead of cloud notification providers.

Local models should be supported architecturally, but quality should be benchmarked per client. The product should not promise that local models always match cloud model extraction quality. A safer promise is private deployment with benchmarked extraction accuracy.

## n8n Decision

n8n can be useful as automation glue at the edges of the system.

Good uses for n8n:

- Watch Gmail or folders.
- Download attachments.
- Trigger IDP ingestion.
- Send WhatsApp, email, Slack, or Teams notifications.
- Move files after processing.
- Call webhooks.
- Create ERP tickets or tasks.

Do not put core domain logic in n8n:

- Matching logic
- Audit trail construction
- Schema validation
- Source-of-truth reconciliation
- Human-review decision policy
- Job state machine

Ironclad IDP core must remain the system of record for decisions and auditability.

## ASAP 3-Way Matching Milestone

The immediate milestone is production v1 of the 3-way matching plugin, not a full platform rewrite.

Chosen constraints:

- Use current ERP Postgres tables for purchase order and goods receipt data.
- Keep current frontend and job statuses stable.
- Persist `requires_human` inside `audit_report`.
- Do not add WhatsApp, Gmail, n8n, Odoo, Excel, or folder adapters in this milestone.
- Add the minimum platform boundary needed so the next plugin does not create graph conditionals.

Implementation direction:

1. Add `src/core/contracts.py`.
2. Add `src/core/plugin_base.py`.
3. Add a minimal plugin runner.
4. Migrate existing 3-way logic into a `SupplyChainThreeWayPlugin`.
5. Refactor graph reconciliation to call the plugin runner.
6. Preserve existing `audit_report` and `processing_notification` payloads for frontend compatibility.
7. Add tests around plugin outputs, `requires_human`, and graph integration.

## Guiding Principle

Do not try to predict every client need in advance. Instead, define stable contracts where client-specific chaos can plug in safely.

Every new client requirement should become one of these:

- Client configuration
- Source adapter
- Intake adapter
- Notification adapter
- Matching plugin
- Deployment profile

It should not become `if client_id == ...` logic inside the graph.
