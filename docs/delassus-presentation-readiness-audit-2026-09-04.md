# Delassus presentation readiness audit

Date: 2026-09-04  
Scope: current working tree, live Docker stack, Delassus dossier workflow, rule administration, review UI, OCR/extraction, queues, persistence, authentication, reporting, and presentation operations.

## Verdict

Ironclad is **not ready for a live Delassus presentation today**.

The project has a credible pilot architecture and a real evidence-based workflow, but the running application is unavailable past its loading screen, the processing worker and outbox dispatcher cannot connect to Postgres, and the rule administration experience is incomplete and misleading. The local Paddle extraction logic is also tailored to the current demo documents and cannot yet be presented as a general Delassus document engine.

It can become ready for a **controlled pilot presentation** after a focused recovery and UX pass. It is not ready for an unscripted trial with arbitrary Delassus files or for production deployment.

## Readiness scorecard

| Area | Score | Current judgment |
| --- | ---: | --- |
| Live demo reliability | 1/5 | The browser remains on `Ouverture de votre espace de travail…`; API health is degraded; worker and outbox restart. |
| Operator clarity | 2/5 | Import is understandable, but statuses, rules, decisions, and next actions require technical knowledge. |
| Rule administration | 1/5 | The UI cannot express or safely preview the available rule model. One visible template is submitted incorrectly. |
| Review experience | 3/5 | The PDF/fact/discrepancy layout is a useful foundation, but it exposes raw codes and lacks evidence highlighting. |
| Architecture | 3/5 | Good boundaries and delivery semantics for a pilot; client/provider selection and rule evaluation are incomplete. |
| OCR/extraction generality | 1/5 | OCR is real, but much of the deterministic extraction is hard-coded to values in the demo dossier. |
| Testability | 4/5 | The focused backend suite passes 52 tests. There is no verified browser/end-to-end suite for the authenticated Delassus path. |
| Security for a controlled local demo | 3/5 | Auth is enforced, but all users are super-admin and PDF URLs are public. |
| **Overall presentation readiness** | **18/40** | **Recoverable controlled pilot; do not present the current live stack.** |

## What is genuinely strong

- A dossier groups several source PDFs and waits for all jobs before generating one decision.
- Creation of the case, source records, jobs, audit event, and outbox events occurs in one database transaction.
- Redis Streams provides at-least-once transport, pending-message recovery, acknowledgements, and persisted retry scheduling.
- OCR evidence retains the source document, page, text, confidence, and bounding box.
- Review writes use a decision version and idempotency key, which protects against stale or repeated decisions.
- Reports, notifications, review history, and audit events are persisted around the same decision.
- The provider and workflow protocols are useful seams for future OCR or client-specific implementations.
- The backend test suite passed: `52 passed in 12.09s`.

## Presentation blockers

### P0 — The running stack cannot process a dossier

Observed state:

- `/health` returns `degraded` with Redis healthy and Supabase/Postgres unhealthy.
- The database error is `(ENOTFOUND) tenant/user postgres.ztbqbqyjpdbwxutkdmxt not found`.
- `worker` and `outbox` continuously restart because their initial database connection fails.
- The API container is unhealthy.

Impact: an upload cannot reliably create, dispatch, process, or compare a dossier. A presentation that depends on live processing will fail.

Required outcome: correct the active connection string, verify migrations and active rules, then prove one fresh upload reaches `AWAITING_REVIEW` and opens successfully in the browser.

### P0 — The authenticated UI stalls indefinitely

The browser remained on `Ouverture de votre espace de travail…`. `AuthGate` waits for `supabase.auth.getSession()` without an error path or timeout. If session recovery or the Supabase endpoint hangs, the product never shows login, an error, or a retry action.

Impact: Delassus sees a blank light screen with one loading sentence.

Required outcome: add a bounded session check with a French error state and retry/sign-in route, then test signed-out, expired-session, provider-unavailable, and signed-in states.

### P0 — Rule creation does not match rule evaluation

The current admin screen presents `EXACT_MATCH`, `FIELD_REQUIRED`, and `REQUIRED_DOCUMENT` with the same `field_path` input. The evaluator expects `REQUIRED_DOCUMENT.parameters.document_type`, so a required-document rule created by this UI has no document type and fails as `unknown`.

Other correctness gaps:

- `EXACT_MATCH` passes when exactly one non-empty value exists; it does not prove that two intended document types agree.
- `authoritative_document_type` and `compared_document_type` exist in the model but are not used by exact-match evaluation.
- `AUTHORITY_PRECEDENCE` reads an authority value from `parameters`, while the API model stores a top-level authority field.
- Numeric tolerance and date-window templates always become manual review because their evaluators are not implemented.
- Activating a ruleset replaces the built-in fallback reconciliation. Checks omitted from that active version are no longer performed.
- No per-rule PASS/FAIL/NOT_APPLICABLE records are written to `rule_evaluation_results`.

Impact: the UI can create a rule that looks valid but does not enforce the business meaning the operator intended.

Required outcome: define and test the evaluator contract first, then build a guided rule form that only offers combinations the backend fully supports.

### P0 — The local extraction is a demo-specific adapter

PaddleOCR genuinely recognizes text and returns confidence and boxes. The step that converts text to business fields contains literal demo values such as container `767208`, vessel `WASA EXPRESS`, exporter `ONDUPET`, quantity `883.728`, and goods value patterns around `15.792,2x`.

Impact: the seven prepared PDFs can work while a new, valid Delassus dossier silently produces missing facts. This is acceptable for a labeled technical prototype, but it must not be described as general extraction accuracy.

Required outcome: present the current files as a controlled example. Before a live-file pilot, replace literal-value patterns with label/layout-based extraction and measure field accuracy on 30–50 reviewed representative dossiers.

## Major UX findings

### P1 — Rule setup speaks implementation language

The operator sees `Rulesets`, `EXACT_MATCH`, `FIELD_REQUIRED`, `REQUIRED_DOCUMENT`, and a free-text `Field path`. There is no explanation of the effect, documents compared, severity, outcome, or what will happen after activation. The operator must know names such as `declaration_number`.

The screen supports one rule when a ruleset is created. It cannot add another rule, edit a draft, remove a rule, clone a version, inspect a complete rule, or test a rule against a dossier. The list only shows a name, version, status, and count.

### P1 — Clean dossiers have no clear success path

The active evaluator returns `REVIEW_REQUIRED` even when every configured rule passes. The workflow also has `allow_automatic_ready=False`. As implemented, a Delassus dossier cannot reach `READY` through the normal local path. The review UI therefore offers `Valider avec réserve` even for a clean dossier.

Impact: a client will reasonably ask why a dossier with no discrepancy must be accepted “with reservation.” Decide whether the pilot is human-validation-only or supports automatic readiness, then name the states and actions consistently.

### P1 — The product has two visual languages

The dossier list and detail use a light slate/blue interface. Administration, notifications, loading/error screens, and legacy modules still use dark zinc/emerald styling. French and English also coexist within the same active journey: table headers, empty states, errors, notifications, statuses, and rule administration remain English or raw codes.

Impact: it feels assembled from separate prototypes and weakens trust in a document-control product.

### P1 — The import flow promises three steps but does not show them

The screen says `Étape 1 sur 3`, but there is no visible step 2 or 3. It does not explain when OCR begins, what is compared, whether sender/issuer are optional, or how long processing may take. There is no per-file upload/processing progress.

### P1 — Evidence is available but not presented as proof

Clicking a compared value opens the correct document/page, but the stored bounding box is not drawn over the PDF. Raw field paths, raw document types, raw rule IDs, and confidence decimals are shown. A Delassus reviewer needs business labels, source document names, and a highlighted evidence region.

### P1 — Document privacy conflicts with authentication

The application requires Supabase authentication, while uploaded PDFs are returned and embedded through a public bucket URL. Anyone with a URL can bypass the application session if the bucket is public.

For a controlled presentation, use synthetic documents only. Private storage and short-lived signed URLs are required before real Delassus documents are used.

### P1 — Roles are not modeled for real use

Every dossier and administration endpoint requires `PLATFORM_SUPER_ADMIN`. There is no Delassus operator, reviewer, or administrator role. The client identifier is fixed in the frontend.

This is acceptable for one controlled pilot account. It is not a production authorization model.

## Technical UI audit

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Accessibility | 1/4 | Several controls rely on placeholders; some selects have no associated label; document tabs lack selected-state semantics; 28–32 px controls miss common touch-target guidance; document language is `en` while the main UI is French. |
| Performance | 2/4 | The dossier list and detail poll forever every 5/4 seconds, including resolved records; the list loads 100 cases without pagination; external Google fonts make a clean build network-dependent. |
| Responsive design | 2/4 | Main pages stack at smaller widths, but dense tables, raw identifiers, narrow issuer controls, and small actions remain difficult on touch screens. Authenticated responsive behavior could not be visually verified. |
| Theming | 1/4 | Shared tokens exist, but active pages hard-code conflicting `slate/blue` and `zinc/emerald` palettes. |
| Product anti-patterns | 2/4 | Familiar navigation and forms are positive; inconsistent screens, metric-card framing, raw codes, and unexplained controls make the product feel generated around components instead of around the operator’s task. |
| **Audit health** | **8/20** | **Poor — coherent UX and state handling need a focused redesign before presentation.** |

## The rule workflow Delassus should see

Replace the current free-form panel with a six-step guided flow:

1. **Name the version** — for example, `Contrôles import Delassus — version pilote`.
2. **Choose a business check** — `Document obligatoire`, `Champ obligatoire`, `Valeurs identiques`, later `Tolérance numérique` and `Écart de dates`.
3. **Choose the field and sources** — friendly field labels plus explicit document types, such as `Numéro de conteneur` in `DUM/MLV` and `Connaissement`.
4. **Choose the consequence** — `Demander une vérification` or `Bloquer le dossier`, with severity explained separately.
5. **Preview the result** — one plain French sentence: “Si les numéros de conteneur diffèrent entre la DUM et le connaissement, le dossier est bloqué.” Test it against a selected sample dossier.
6. **Save the draft, review the whole version, then activate it** — activation shows which previous version will retire and requires a reason.

Suggested initial rules for the presentation, explicitly labeled **proposed and awaiting Delassus confirmation**:

| Rule name shown to the user | Condition | Suggested outcome |
| --- | --- | --- |
| Même numéro de déclaration | Compare the declaration number in the agreed customs documents | Block |
| Même numéro de connaissement | Compare the B/L number in the agreed customs and transport documents | Block |
| Même numéro de conteneur | Compare the container number in the agreed customs, B/L, and release documents | Block |

Required-document and required-field rules should only be added after Delassus confirms which documents and fields are mandatory for each dossier type.

## The daily operator journey

1. Open **Dossiers** and select **Nouveau dossier**.
2. Add all PDFs belonging to the same shipment.
3. Enter the shipment reference; choose sender and issuer when known.
4. Select **Lancer l’analyse**. Show upload and processing progress by file.
5. Open the result summary: `3 contrôles réussis`, `1 écart`, `2 informations à confirmer`.
6. Select an issue to open the source page with the exact text highlighted.
7. Choose **Valider**, **Bloquer**, or **Demander une correction**, add a reason, and confirm.
8. Download the audit report when needed.

## Architecture judgment

The architecture is credible for an MVP because the durable business state lives in Postgres, async delivery uses an outbox, workers are retriable, evidence is modeled explicitly, and decisions are versioned. This is a better foundation than the current UI communicates.

It is not yet a mature multi-client platform:

- `ClientConfig.provider_profile` and `ruleset_version` are declared but do not select the runtime provider or active ruleset.
- The Compose worker chooses one global `DOCUMENT_PROVIDER` for all clients.
- The workflow registry currently contains one dossier workflow.
- The repository is split between a legacy invoice/LangGraph path and the newer dossier path in the same API and worker.
- LangGraph uses an in-memory checkpointer for the legacy path, so graph checkpoint recovery is not durable across restarts.
- Operational monitoring, dead-letter handling, backup/restore proof, OCR accuracy metrics, and browser end-to-end tests are absent.

These items do not prevent a controlled Delassus demonstration after the P0 fixes. They prevent production and broad platform claims.

## Recommended presentation scope

Say:

> “This is a controlled pilot showing how an import dossier can be classified, read, compared, and reviewed with traceable evidence. The rules shown are a proposal to validate with Delassus.”

Demonstrate:

- one prepared clean/review dossier;
- one prepared mismatch dossier;
- evidence from a compared value to the source page;
- a human decision with a reason;
- the generated PDF report;
- a read-only view of the proposed rule version.

Do not run an arbitrary document or create a rule live until the extraction and rule-builder blockers are resolved.

## Work sequence

1. Recover the database connection and prove a fresh end-to-end dossier run.
2. Fix the indefinite authentication loading state.
3. Repair the rule contract and add evaluator tests for missing sources, scoped comparison, and required documents.
4. Replace the admin panel with the guided rule builder and a safe proposed Delassus preset.
5. Unify French copy, status labels, and the light visual system across the active Delassus routes.
6. Improve review evidence labels and bounding-box highlighting.
7. Replace demo-value extraction rules with general patterns, then benchmark representative dossiers.
8. Run authenticated browser QA at desktop, tablet, and mobile sizes; rehearse the demo twice with a fallback report.

## Verification performed

- Live Docker state and `/health` inspected on 2026-09-04.
- Live browser route `http://localhost:3000/dossiers` inspected; it remained on the authentication loading state.
- Backend: `python -m pytest -q -p no:cacheprovider` → `52 passed in 12.09s`.
- Current frontend Docker build attempted. It failed while fetching JetBrains Mono from Google Fonts; the currently running frontend image is therefore not proof that the current source builds cleanly.
- Host lint/build could not be run because the interrupted dependency installation did not provide local `eslint` or `next` binaries.
- The authenticated dossier/admin/detail screens could not be visually assessed because the live auth/database path is unavailable. Their interaction and responsive findings are based on complete source inspection.
