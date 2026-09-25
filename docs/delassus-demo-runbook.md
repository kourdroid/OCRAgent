# Delassus Demo Runbook

## Start

From the project root:

```powershell
docker compose up -d --build
docker compose ps
```

Open the dashboard at http://localhost:3000/dossiers.

## Demonstration Flow

1. Select `Review queue` to show the live Delassus dossier.
2. Open the dossier and explain that the case groups all source files while each classified document remains traceable by page.
3. Select a document tab, then use the PDF viewer and extracted facts to show the evidence-backed review surface.
4. Point out the conservative decision: `REVIEW_REQUIRED` means the system has not automatically cleared the dossier.
5. Show the JSON and PDF report links. Both are generated from the same audit model.
6. During a live approval demonstration, enter a reviewer comment before using Override or Reject. This resolves the case and is intentional.

## Prepared Cases

- Live review case: `cb6b4dfc-590b-4684-aafc-e0558a1b9ac8`
- Resolved fallback: `55690ec3-c0a6-4cbf-b29c-3ed7822426d3`

## Offline Fallback

The pre-generated JSON and PDF reports are available in:

`C:\Users\Mehdi\Documents\Delassus\Demo Output`

## Honest Scope Statement

This is a controlled pilot demonstration. It processes French and English import documents through the local PaddleOCR provider, preserves evidence and human review, and produces audit reports. It is not yet a production deployment: authentication, RLS/private document access, validated accuracy benchmarking, and live ERP or PortNet integration remain future gates.
