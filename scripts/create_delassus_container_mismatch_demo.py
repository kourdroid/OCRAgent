"""Create an isolated, clearly labelled Delassus review-demo dossier.

The script clones an existing dossier and changes only the copied DUM container
number.  It is a seed utility for demonstrations, not a processing workflow.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import sys
import uuid

import asyncpg
import requests
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas


SOURCE_CASE_ID = "ca540488-8cce-4704-96a8-649d5105dda8"
SOURCE_DUM_SEGMENT_ID = "90b83490-d4b9-42c5-9f35-1fe3ba67e2d6"
DEMO_CONTAINER_NUMBER = "9999-99"


def quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


PRIMARY_KEYS = {
    "dossier_cases": "case_id",
    "document_artifacts": "document_id",
    "extraction_results": "extraction_id",
    "decision_results": "decision_id",
}


def render_demo_pdf(source_pdf: bytes) -> bytes:
    reader = PdfReader(io.BytesIO(source_pdf))
    writer = PdfWriter()

    for index, page in enumerate(reader.pages):
        if index == 0:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_buffer = io.BytesIO()
            overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))
            overlay.setFillColor(HexColor("#B42318"))
            overlay.rect(width * 0.04, height * 0.86, width * 0.92, height * 0.10, fill=1, stroke=0)
            overlay.setFillColor(white)
            overlay.setFont("Helvetica-Bold", 13)
            overlay.drawString(width * 0.06, height * 0.92, f"DEMO EXCEPTION - CONTAINER NUMBER: {DEMO_CONTAINER_NUMBER}")
            overlay.setFont("Helvetica", 8)
            overlay.drawString(width * 0.06, height * 0.885, "Synthetic training copy for the review-workflow demonstration only")
            overlay.save()
            overlay_buffer.seek(0)
            page.merge_page(PdfReader(overlay_buffer).pages[0])
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


async def copy_row(connection: asyncpg.Connection, table: str, row: asyncpg.Record, *, overrides: dict[str, object], exclude: set[str]) -> uuid.UUID:
    columns = [column for column in row.keys() if column not in exclude and column not in overrides]
    columns.extend(overrides.keys())
    values = [row[column] for column in row.keys() if column in columns and column not in overrides]
    values.extend(overrides[column] for column in overrides)
    statement = (
        f"INSERT INTO {quoted_identifier(table)} ({', '.join(quoted_identifier(column) for column in columns)}) "
        f"VALUES ({', '.join(f'${index}' for index in range(1, len(columns) + 1))}) "
        f"RETURNING {quoted_identifier(PRIMARY_KEYS[table])}"
    )
    return await connection.fetchval(statement, *values)


async def main() -> None:
    required = ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SECRET_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    connection = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    try:
        source_case = await connection.fetchrow("SELECT * FROM dossier_cases WHERE case_id = $1::uuid", SOURCE_CASE_ID)
        if source_case is None:
            raise RuntimeError("The source Delassus case was not found")

        artifacts = await connection.fetch(
            "SELECT * FROM document_artifacts WHERE case_id = $1::uuid ORDER BY created_at, document_id",
            SOURCE_CASE_ID,
        )
        target_segment = next((row for row in artifacts if str(row["document_id"]) == SOURCE_DUM_SEGMENT_ID), None)
        if target_segment is None:
            raise RuntimeError("The source DUM segment was not found")
        source_dum_id = target_segment["source_artifact_id"]

        source_response = requests.get(target_segment["file_url"], timeout=45)
        source_response.raise_for_status()
        demo_pdf = render_demo_pdf(source_response.content)
        demo_hash = hashlib.sha256(demo_pdf).hexdigest()
        case_id = uuid.uuid4()
        demo_path = f"dossiers/delassus/{case_id}/demo-container-mismatch-DUM-7672-08.pdf"
        api_url = os.environ["SUPABASE_URL"].rstrip("/")
        headers = {
            "apikey": os.environ["SUPABASE_SECRET_KEY"],
            "Authorization": f"Bearer {os.environ['SUPABASE_SECRET_KEY']}",
            "Content-Type": "application/pdf",
            "User-Agent": "ironclad-ocr-demo-seed/1.0",
            "x-upsert": "false",
        }
        upload_response = requests.post(
            f"{api_url}/storage/v1/object/ironclad-docs/{demo_path}", headers=headers, data=demo_pdf, timeout=45
        )
        upload_response.raise_for_status()
        demo_url = f"{api_url}/storage/v1/object/public/ironclad-docs/{demo_path}"

        try:
            async with connection.transaction():
                await copy_row(
                    connection,
                    "dossier_cases",
                    source_case,
                    overrides={
                        "case_id": case_id,
                        "external_reference": "DELASSUS-DEMO-CONTAINER-MISMATCH-20260818",
                        "status": "AWAITING_REVIEW",
                    },
                    exclude={"case_id", "created_at", "updated_at"},
                )

                document_ids: dict[uuid.UUID, uuid.UUID] = {}
                sources = [row for row in artifacts if row["artifact_kind"] != "SEGMENT"]
                segments = [row for row in artifacts if row["artifact_kind"] == "SEGMENT"]
                for row in [*sources, *segments]:
                    is_modified_dum = row["document_id"] == source_dum_id or row["document_id"] == target_segment["document_id"]
                    overrides: dict[str, object] = {
                        "document_id": uuid.uuid4(),
                        "case_id": case_id,
                    }
                    if row["source_artifact_id"]:
                        overrides["source_artifact_id"] = document_ids[row["source_artifact_id"]]
                    if is_modified_dum:
                        overrides.update({"storage_path": demo_path, "file_url": demo_url, "sha256": demo_hash})
                    new_document_id = await copy_row(
                        connection,
                        "document_artifacts",
                        row,
                        overrides=overrides,
                        exclude={"document_id", "case_id", "created_at", "updated_at"},
                    )
                    document_ids[row["document_id"]] = new_document_id

                extractions = await connection.fetch(
                    "SELECT * FROM extraction_results WHERE document_id = ANY($1::uuid[]) ORDER BY created_at",
                    list(document_ids.keys()),
                )
                for row in extractions:
                    new_extraction_id = await copy_row(
                        connection,
                        "extraction_results",
                        row,
                        overrides={"extraction_id": uuid.uuid4(), "document_id": document_ids[row["document_id"]]},
                        exclude={"extraction_id", "document_id", "run_id", "created_at"},
                    )
                    if row["document_id"] == target_segment["document_id"]:
                        normalized = json.loads(row["normalized_data"])
                        for fact in normalized.get("facts", []):
                            if fact.get("field_path") == "container_number":
                                fact.update(
                                    {
                                        "value": DEMO_CONTAINER_NUMBER,
                                        "source_text": f"DEMO EXCEPTION - CONTAINER NUMBER: {DEMO_CONTAINER_NUMBER}",
                                        "confidence": 1.0,
                                        "bbox": [0.04, 0.86, 0.96, 0.96],
                                    }
                                )
                        await connection.execute(
                            "UPDATE extraction_results SET normalized_data = $1::jsonb WHERE extraction_id = $2::uuid",
                            json.dumps(normalized),
                            new_extraction_id,
                        )

                prior_decision = await connection.fetchrow(
                    "SELECT * FROM decision_results WHERE case_id = $1::uuid ORDER BY decision_version DESC, created_at DESC LIMIT 1",
                    SOURCE_CASE_ID,
                )
                if prior_decision is None:
                    raise RuntimeError("The source case has no decision to clone")
                dum_document_id = document_ids[target_segment["document_id"]]
                bol_document_id = next(
                    document_ids[row["document_id"]]
                    for row in segments
                    if row["document_type"] == "BILL_OF_LADING"
                )
                discrepancy = {
                    "rule_id": "transport.container_number_match.v1",
                    "severity": "critical",
                    "message": "Container number differs between the DUM and Bill of Lading.",
                    "values": [
                        {
                            "document_id": str(dum_document_id),
                            "field_path": "container_number",
                            "value": DEMO_CONTAINER_NUMBER,
                            "evidence": {
                                "document_id": str(dum_document_id),
                                "field_path": "container_number",
                                "page": 1,
                                "source_text": f"DEMO EXCEPTION - CONTAINER NUMBER: {DEMO_CONTAINER_NUMBER}",
                                "confidence": 1.0,
                                "bbox": [0.04, 0.86, 0.96, 0.96],
                            },
                        },
                        {
                            "document_id": str(bol_document_id),
                            "field_path": "container_number",
                            "value": "767208",
                        },
                    ],
                }
                report_payload = {
                    "report_version": "demo-1",
                    "scenario": "Synthetic visible container-number mismatch for review workflow demonstration",
                    "case_id": str(case_id),
                    "decision": "BLOCKED",
                    "discrepancies": [discrepancy],
                }
                decision_id = await copy_row(
                    connection,
                    "decision_results",
                    prior_decision,
                    overrides={
                        "decision_id": uuid.uuid4(),
                        "case_id": case_id,
                        "status": "BLOCKED",
                        "summary": "Demo scenario: DUM container 9999-99 conflicts with Bill of Lading container 767208.",
                        "discrepancies": json.dumps([discrepancy]),
                        "report_payload": json.dumps(report_payload),
                    },
                    exclude={"decision_id", "case_id", "created_at"},
                )
                await connection.execute(
                    """INSERT INTO review_tasks (case_id, decision_id, client_id, status, idempotency_key)
                       VALUES ($1, $2, $3, 'PENDING', $4)""",
                    case_id,
                    decision_id,
                    source_case["client_id"],
                    f"demo-container-mismatch:{case_id}",
                )
                await connection.execute(
                    """INSERT INTO audit_events (case_id, client_id, event_type, event_data)
                       VALUES ($1, $2, 'DEMO_EXCEPTION_SEEDED', $3::jsonb)""",
                    case_id,
                    source_case["client_id"],
                    json.dumps(
                        {
                            "synthetic": True,
                            "message": "A visible DUM container mismatch was seeded for a review-workflow demonstration.",
                            "source_case_id": SOURCE_CASE_ID,
                        }
                    ),
                )
        except Exception:
            requests.delete(f"{api_url}/storage/v1/object/ironclad-docs/{demo_path}", headers=headers, timeout=30)
            raise

        print(json.dumps({"case_id": str(case_id), "decision": "BLOCKED", "document": "DUM 7672-08.pdf"}))
    finally:
        await connection.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"Demo dossier creation failed: {error}", file=sys.stderr)
        raise
