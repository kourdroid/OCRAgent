# Ironclad — Delassus Presentation Recovery Plan

**Date:** 2026-09-04  
**Status:** Draft for approval — planning only, no implementation authorized yet  
**Source:** `delassus-presentation-readiness-audit-2026-09-04.md`

## 1. Goal

Prepare Ironclad for a credible Delassus presentation in which a non-technical operator can:

1. create a dossier;
2. import shipment documents;
3. understand what the OCR extracted;
4. see which business controls were applied;
5. locate the evidence inside the source document;
6. understand why the dossier is ready, requires review, or is blocked;
7. validate the dossier and download a report.

The presentation must demonstrate a controlled, truthful workflow. It must not imply that Ironclad can reliably process arbitrary Delassus documents until that capability is measured on representative samples.

## 2. Recommended scope

### Presentation-ready scope

- One stable dossier workflow, from import to report.
- French-first, light, familiar operational interface.
- Three supported rule families only:
  - document required;
  - field required;
  - equality between a field in two or more named document types.
- Clear outcomes:
  - **Prêt à valider** when all applicable controls pass with sufficient evidence;
  - **À vérifier** when evidence is missing, uncertain, or not applicable;
  - **Bloqué** when a blocking business rule fails.
- Page-level evidence with the relevant zone highlighted.
- Controlled demonstration documents with known expected results.
- A clean dossier scenario, a discrepancy scenario, and an OCR/unknown-document scenario.

### Explicitly outside the presentation sprint

- Claiming robust extraction for every Delassus template.
- Full multi-tenant production authorization.
- ERP integration.
- A general no-code rule language.
- Numeric/date rules before their evaluator behavior is implemented and tested.
- Redesigning the legacy invoice/LangGraph workflow.

The legacy path should be hidden from the Delassus demonstration instead of being expanded during this sprint.

## 3. Product decisions to make explicit

### 3.1 Processing without business rules

Importing a document should always perform technical processing: file validation, OCR, document classification, field extraction, confidence checks, and evidence capture. Those are system safeguards, not configurable business rules.

If no business ruleset is active, the product must say so clearly and return **À vérifier — aucun référentiel actif**. It must not silently pretend that a business comparison occurred.

### 3.2 Processing with an active ruleset

The engine should combine:

- always-on technical safeguards; and
- the active versioned business ruleset.

Activating a business ruleset must never disable OCR confidence checks, unknown-document handling, or missing-evidence safeguards.

### 3.3 Decision policy

- Any failed active rule whose consequence is **Bloquer** makes the dossier **Bloqué**.
- Any missing source, ambiguous value, low-confidence value, or unsupported comparison makes the dossier **À vérifier**.
- A dossier becomes **Prêt à valider** only when every applicable active rule passes and all required evidence is present.
- Human validation remains the final action; automatic readiness is not automatic approval.

### 3.4 Rules shown in the interface

The presentation UI must expose only rule behavior that exists in the evaluator. Raw enum codes such as `EXACT_MATCH` or `REVIEW_REQUIRED` must never be shown to operators.

The first proposed pilot controls are placeholders until Delassus confirms them:

1. declaration number matches between named customs documents;
2. bill of lading number matches between named customs/transport documents;
3. container number matches between named customs, transport, and release documents;
4. required documents and required fields defined only after Delassus confirms the dossier checklist.

## 4. Target operator journey

### Step 1 — Create

The operator chooses **Nouveau dossier**, enters a business reference and optional sender/issuer, then adds all relevant PDFs.

### Step 2 — Analyze

The primary action is **Lancer l’analyse**. Each file shows an understandable status: uploaded, queued, OCR in progress, analyzed, or failed with a recovery action.

### Step 3 — Understand

The result opens with a business summary such as:

> 3 contrôles conformes · 1 écart · 2 éléments à confirmer

No raw internal status, field key, or rule type should appear in the primary workflow.

### Step 4 — Review evidence

Selecting a control shows:

- the expected condition in plain French;
- values compared and their source documents;
- OCR confidence;
- the exact source page with the evidence zone highlighted;
- an explicit explanation when a comparison could not be performed.

### Step 5 — Decide

The operator can **Valider**, **Bloquer**, or **Relancer l’analyse**, with a reason where required. The report records the ruleset version, evidence, system decision, human decision, timestamp, and actor.

## 5. Target rule-authoring journey

1. Open **Référentiels de contrôle**.
2. Create a draft version and give it a clear name.
3. Add a control by choosing a business intent:
   - Exiger un document;
   - Exiger une information;
   - Comparer la même information entre plusieurs documents.
4. Select the field and explicit source document types.
5. Choose the consequence independently from severity:
   - demander une vérification;
   - bloquer le dossier.
6. Read a generated French preview, for example:

   > Bloquer le dossier si le numéro de conteneur du connaissement diffère de celui de la déclaration.

7. Test the draft against a sample dossier.
8. Review the complete version, then activate it with a reason.

Editing an active version should create a new draft. Previous versions remain immutable and auditable.

## 6. Delivery plan

### Phase 0 — Safeguard and establish the baseline

**Estimated effort:** 0.5 day  
**Purpose:** avoid losing existing work and create a trustworthy starting point.

Work:

- inventory the current dirty working tree and separate relevant changes from unrelated user work;
- record current service versions, configuration shape, migrations, and environment prerequisites without exposing credentials;
- preserve a recoverable checkpoint before implementation;
- rerun the backend tests and record the current frontend/runtime failures;
- define the exact three presentation fixtures and their expected results.

Acceptance gate:

- baseline evidence is saved;
- no existing user changes are overwritten;
- the clean, mismatch, and uncertain test dossiers have written expected outcomes.

### Phase 1 — Restore a reliable runnable stack

**Estimated effort:** 0.5–1 day  
**Purpose:** make the application consistently open and process work before redesigning it.

Work:

- correct the database connection configuration and verify the required migrations;
- make API, worker, and outbox services remain healthy after a cold start;
- add a timeout and an actionable failure state to session initialization;
- remove the build-time dependency on remote Google Fonts by using a bundled or system-safe font stack;
- ensure the frontend can show signed-out and signed-in states instead of waiting forever;
- produce one documented start/reset procedure for the presentation machine.

Acceptance gate:

- `/health` reports healthy dependencies;
- API, worker, outbox, Redis, OCR, and frontend remain stable for at least 10 minutes;
- a cold start reaches an actionable screen within five seconds;
- a fresh frontend build, lint, and backend test run succeed;
- no secret is printed or committed.

### Phase 2 — Correct and simplify the rule domain

**Estimated effort:** 1.5–2 days  
**Purpose:** ensure every visible rule means exactly what the engine executes.

Work:

- define typed, validated parameters for each supported rule family;
- fix required-document parameters so the UI and evaluator use the same document-type contract;
- require explicit source document types for equality rules;
- prevent an equality rule from passing when fewer than two required values are available;
- treat missing or low-confidence sources as **À vérifier**, not as a pass;
- separate severity from consequence and use both consistently;
- combine always-on safeguards with the active business ruleset;
- permit **Prêt à valider** only under the decision policy in section 3.3;
- persist a result row for every evaluated rule, including status, values, evidence, and explanation;
- validate a ruleset before activation and reject unsupported or incomplete definitions;
- add unit, repository, API contract, and decision-policy tests.

Acceptance gate:

- each supported rule has positive, negative, missing-source, and low-confidence tests;
- unsupported rules cannot be created or activated;
- clean fixture → **Prêt à valider**;
- blocking mismatch fixture → **Bloqué**;
- uncertain fixture → **À vérifier**;
- each outcome can be traced to persisted per-rule evidence.

### Phase 3 — Replace the rule form with a guided builder

**Estimated effort:** 2–3 days  
**Purpose:** make rules understandable to an operations manager without knowledge of internal codes.

Work:

- replace the single technical form with draft versions containing multiple controls;
- use French labels, examples, inline guidance, and document/field pickers;
- show only compatible inputs for the selected control type;
- add the plain-language preview and validation summary;
- add a sample-dossier test before activation;
- add version review, activation reason, immutable history, and safe draft editing;
- translate and normalize every ruleset state and error.

Acceptance gate:

- a first-time user can create the three pilot controls without typing JSON or internal identifiers;
- invalid definitions are blocked before submission with a useful explanation;
- the preview sentence corresponds to the evaluator payload;
- activation produces one complete version, not one ruleset per rule;
- active and historical versions are clearly distinguishable.

### Phase 4 — Rebuild the daily dossier experience

**Estimated effort:** 2–3 days  
**Purpose:** turn the product from a technical dashboard into a guided review tool.

Work:

- simplify navigation around **Dossiers**, **Référentiels**, and **Administration**;
- redesign the dossier list with French business statuses and obvious next actions;
- implement the five-step operator journey from section 4;
- show real per-file progress and stop infinite polling with retry/error states;
- replace raw field keys and confidence decimals with readable labels and explanations;
- add an authenticated page-image endpoint and draw the evidence bounding box in the UI;
- make validation, blocking, reprocessing, and report download explicit actions;
- unify the visual system: light surfaces, white cards, navy text, blue primary actions, restrained semantic colors, and accessible control sizes;
- verify common laptop and tablet widths.

Acceptance gate:

- a new operator can complete each presentation scenario without instruction from the developer;
- the screen always answers: what happened, why, where the evidence is, and what to do next;
- every result links to visible source evidence;
- no primary workflow surface contains mixed language, raw enums, raw field paths, or unexplained icons;
- upload, processing, API, and session failures have recoverable states.

### Phase 5 — Remove demo-specific extraction behavior

**Estimated effort:** 2–4 days for the first bounded set; longer depends on Delassus document diversity  
**Purpose:** move from a controlled presentation to a credible pilot.

Work:

- remove hard-coded demo values from deterministic extraction;
- define canonical fields per supported document type;
- extract using labels, spatial relationships, normalization, and documented fallbacks;
- assemble a representative, permissioned evaluation set with Delassus;
- measure field-level precision/recall, document classification accuracy, unsupported cases, and confidence calibration;
- define thresholds that route uncertain extraction to human review;
- keep the evidence chain for every extracted value.

Acceptance gate:

- no literal customer/demo value is embedded in an extractor;
- evaluation metrics are reported per document type and field;
- known unsupported templates fail visibly into review;
- a measured threshold, not intuition, determines pilot readiness.

### Phase 6 — Production security and operational hardening

**Estimated effort:** 3–5 days minimum, subject to deployment and identity requirements  
**Purpose:** prepare for real customer data after the presentation.

Work:

- make document storage private and serve time-limited or authenticated content;
- replace platform-super-admin-only access with operator, reviewer, and administrator roles;
- enforce tenant/client boundaries in repositories and storage paths;
- tighten CORS and environment validation;
- add queue lag, failure, retry, dead-letter, and health observability;
- document backup, restore, retention, deletion, and incident procedures;
- perform a focused threat and privacy review.

Acceptance gate:

- one client cannot access another client's dossier or document;
- PDFs are not publicly addressable;
- least-privilege roles are verified through API tests;
- processing failures are visible and recoverable;
- backup/restore and retention behavior are documented and tested.

### Phase 7 — Presentation QA and rehearsal

**Estimated effort:** 1 day  
**Purpose:** verify the real workflow, not isolated components.

Work:

- run backend, frontend, contract, and authenticated browser tests;
- test cold start, empty state, clean case, mismatch, low-confidence case, failed upload, failed processing, reprocess, human validation, and report download;
- inspect desktop and tablet screenshots for visual consistency and evidence readability;
- verify the generated report against the UI and persisted rule results;
- perform two complete rehearsals from a clean state;
- prepare a short recovery runbook and offline screenshots/report fallback.

Acceptance gate:

- all required checks pass from a fresh source checkout and clean application state;
- both rehearsals complete without developer intervention;
- the presentation narrative does not claim capability beyond the tested fixtures;
- the fallback material matches the current build.

## 7. Sequence and release gates

| Gate | Included phases | Decision |
|---|---:|---|
| Stable engineering baseline | 0–1 | Continue only when the stack is healthy and reproducible. |
| Trustworthy rules engine | 2 | Continue only when the three fixture outcomes and per-rule evidence are correct. |
| Usable presentation product | 3–4 | Continue only after a novice walkthrough succeeds. |
| Presentation approval | 7 | Present only after two clean rehearsals. |
| Controlled customer pilot | 5 plus relevant parts of 6 | Start only after representative extraction measurement and privacy/role controls. |

Phases 5 and 6 should not be allowed to delay the controlled presentation, but they are mandatory before describing Ironclad as production-ready.

## 8. Initial implementation map

Likely areas affected after approval:

- Backend rule model/evaluation, dossier processing, repositories, admin routes, auth, storage, schemas, and migrations.
- Frontend rules administration, dossier list/detail, upload flow, authentication gate, API types, navigation, global styles, and notifications.
- Backend and frontend tests, browser fixtures, demo data, operating runbook, and presentation script.

Before editing, each change must be mapped against the current dirty tree so existing work is preserved.

## 9. Definition of presentation-ready

Ironclad is ready for the Delassus presentation only when all of the following are true:

- the stack starts reliably from documented instructions;
- authentication succeeds or fails with an actionable message;
- the operator journey works end to end for all three fixtures;
- the rule builder uses plain French and exposes only implemented behavior;
- comparisons name their source documents and cannot pass with insufficient evidence;
- clean, uncertain, and blocking outcomes follow the documented policy;
- every decision is backed by visible page evidence and persisted rule results;
- sensitive PDFs are not exposed through public URLs;
- the active presentation surfaces are visually consistent, responsive, and free of raw technical codes;
- tests, builds, and authenticated browser checks pass;
- two rehearsals complete without manual repair;
- all claims in the presentation are limited to measured or directly demonstrated capability.

## 10. Schedule recommendation

A realistic target for a controlled, fixture-based presentation is **approximately 6–9 focused development days**, assuming database access and the current services can be restored without an external dependency delay.

A credible Delassus pilot is a separate milestone. Its duration depends primarily on receiving representative document samples and confirmed business rules; a preliminary estimate is **an additional 2–4 weeks**, including extraction benchmarking and essential security/role hardening.

These are planning estimates, not commitments. Phase 0 establishes the evidence needed to refine them.

## 11. Inputs required from Delassus before pilot activation

- the authoritative list of required document types;
- the exact fields that must be compared and between which documents;
- which discrepancies block a dossier versus require review;
- accepted formatting/tolerance rules for identifiers, quantities, currency, weights, and dates;
- representative, permissioned sample dossiers including difficult and failed cases;
- expected user roles, approval authority, retention, and hosting constraints.

For the presentation, unconfirmed business rules must be labeled **proposed demonstration controls**.

## Approval checkpoint

No product code should be changed from this plan alone. Once this order and scope are approved, implementation should start with Phase 0 and Phase 1, followed by a verified status report before proceeding to the rules engine and UI.
