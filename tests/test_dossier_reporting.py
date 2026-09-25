from __future__ import annotations

from src.dossiers.reporting import build_canonical_report, render_report_pdf


def test_json_and_pdf_reports_use_the_same_canonical_record() -> None:
    case_record = {
        "case": {
            "case_id": "case-1",
            "client_id": "delassus",
            "external_reference": "SHIP-1",
            "status": "AWAITING_REVIEW",
        },
        "sources": [],
        "documents": [
            {
                "document_id": "doc-1",
                "document_type": "BAD",
                "page_start": 1,
                "page_end": 1,
                "facts": [
                    {
                        "field_path": "bill_of_lading_number",
                        "value": "BL-1",
                        "page": 1,
                        "confidence": 0.99,
                        "source_text": "BL-1",
                    }
                ],
            }
        ],
        "decision": {
            "decision_id": "decision-1",
            "decision_version": 1,
            "status": "REVIEW_REQUIRED",
            "ruleset_id": "delassus_pilot",
            "ruleset_version": "1",
            "summary": "Manual review required.",
            "discrepancies": [],
        },
        "reviews": [],
        "audit_events": [],
    }

    report = build_canonical_report(case_record)
    pdf = render_report_pdf(report)

    assert report.case["case_id"] == "case-1"
    assert report.decision["status"] == "REVIEW_REQUIRED"
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
