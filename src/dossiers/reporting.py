from __future__ import annotations

import io
import json
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.dossiers.models import DossierReport


def build_canonical_report(case_record: dict[str, Any]) -> DossierReport:
    decision = case_record.get("decision")
    if not decision:
        raise ValueError("The dossier does not have a decision yet")
    return DossierReport(
        case=case_record["case"],
        sources=case_record.get("sources", []),
        documents=case_record["documents"],
        decision=decision,
        reviews=case_record["reviews"],
        audit_events=case_record["audit_events"],
    )


def _safe_text(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def render_report_pdf(report: DossierReport) -> bytes:
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Ironclad dossier report {report.case.get('case_id', '')}",
    )
    story: list[Any] = [
        Paragraph("Ironclad Dossier Audit Report", styles["Title"]),
        Spacer(1, 5 * mm),
        Table(
            [
                ["Case", _safe_text(report.case.get("case_id"))],
                ["Client", _safe_text(report.case.get("client_id"))],
                ["External reference", _safe_text(report.case.get("external_reference"))],
                ["Lifecycle", _safe_text(report.case.get("status"))],
                ["Decision", _safe_text(report.decision.get("status"))],
                ["Decision version", _safe_text(report.decision.get("decision_version"))],
                ["Ruleset", _safe_text(report.decision.get("ruleset_id"))],
                ["Ruleset version", _safe_text(report.decision.get("ruleset_version"))],
            ],
            colWidths=[42 * mm, 132 * mm],
        ),
        Spacer(1, 6 * mm),
        Paragraph(_safe_text(report.decision.get("summary")), styles["BodyText"]),
        Spacer(1, 7 * mm),
        Paragraph("Documents and evidence", styles["Heading2"]),
    ]

    if report.sources:
        manifest_rows = [["File", "Channel", "Sender", "Issuer", "Provenance"]]
        for source in report.sources:
            manifest_rows.append(
                [
                    _safe_text(source.get("original_filename")),
                    _safe_text(source.get("intake_channel")),
                    _safe_text(source.get("sender_party_name")),
                    _safe_text(source.get("issuer_party_name")),
                    _safe_text(source.get("provenance_status")),
                ]
            )
        manifest = Table(manifest_rows, repeatRows=1, colWidths=[45 * mm, 28 * mm, 35 * mm, 35 * mm, 31 * mm])
        manifest.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e4e7")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#a1a1aa")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ]))
        story.extend([Paragraph("Source manifest", styles["Heading2"]), manifest, Spacer(1, 6 * mm)])

    for document_item in report.documents:
        story.extend(
            [
                Spacer(1, 3 * mm),
                Paragraph(
                    (
                        f"{_safe_text(document_item.get('document_type'))} - "
                        f"pages {_safe_text(document_item.get('page_start'))}-"
                        f"{_safe_text(document_item.get('page_end'))}"
                    ),
                    styles["Heading3"],
                ),
            ]
        )
        fact_rows = [["Field", "Value", "Page", "Confidence", "Evidence"]]
        for fact in document_item.get("facts") or []:
            fact_rows.append(
                [
                    _safe_text(fact.get("field_path")),
                    _safe_text(fact.get("value")),
                    _safe_text(fact.get("page")),
                    f"{float(fact.get('confidence') or 0):.2f}",
                    _safe_text(fact.get("source_text")),
                ]
            )
        if len(fact_rows) == 1:
            fact_rows.append(["-", "-", "-", "-", "No facts extracted"])
        table = Table(
            fact_rows,
            repeatRows=1,
            colWidths=[34 * mm, 38 * mm, 14 * mm, 22 * mm, 66 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e4e7")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#a1a1aa")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEADING", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(table)

    story.extend([PageBreak(), Paragraph("Decision discrepancies", styles["Heading2"])])
    discrepancies = report.decision.get("discrepancies") or []
    if not discrepancies:
        story.append(Paragraph("No discrepancies recorded.", styles["BodyText"]))
    for discrepancy in discrepancies:
        story.extend(
            [
                Paragraph(
                    (
                        f"{_safe_text(discrepancy.get('rule_id'))} "
                        f"[{_safe_text(discrepancy.get('severity'))}]"
                    ),
                    styles["Heading3"],
                ),
                Paragraph(_safe_text(discrepancy.get("message")), styles["BodyText"]),
                Spacer(1, 3 * mm),
            ]
        )

    story.extend([Spacer(1, 6 * mm), Paragraph("Review history", styles["Heading2"])])
    if not report.reviews:
        story.append(Paragraph("No review action recorded.", styles["BodyText"]))
    for review in report.reviews:
        story.append(
            Paragraph(
                (
                    f"{_safe_text(review.get('resolution') or review.get('status'))}: "
                    f"{_safe_text(review.get('comment'))}"
                ),
                styles["BodyText"],
            )
        )

    document.build(story)
    return output.getvalue()
