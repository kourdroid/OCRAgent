from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import asyncpg

from src.dossiers.models import DossierCaseContext, DossierDecision, ReviewResolution
from src.infrastructure.supabase_repos import _BaseRepository


class DossierNotFoundError(LookupError):
    pass


class DecisionVersionConflictError(RuntimeError):
    pass


class InvalidReviewResolutionError(RuntimeError):
    pass


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _serialize_row(row: asyncpg.Record | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    for key, value in list(data.items()):
        if isinstance(value, (datetime,)):
            data[key] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            data[key] = str(value)
        elif isinstance(value, Decimal):
            data[key] = float(value)
        elif key in {
            "normalized_data",
            "discrepancies",
            "report_payload",
            "event_data",
            "payload",
            "bbox",
            "metadata",
            "parameters",
            "compared_values",
            "evidence_refs",
        }:
            data[key] = _json_value(value)
    return data


class DossierRepository(_BaseRepository):
    async def is_platform_super_admin(self, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            value = await conn.fetchval(
                """
                SELECT 1 FROM app_users
                WHERE user_id = $1 AND role = 'PLATFORM_SUPER_ADMIN' AND is_active = TRUE
                """,
                uuid.UUID(user_id),
            )
            return bool(value)

    async def list_parties(self, *, client_id: str, active_only: bool = False) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM source_parties
                WHERE client_id = $1 AND ($2::BOOLEAN = FALSE OR is_active = TRUE)
                ORDER BY scope, party_type, name
                """,
                client_id,
                active_only,
            )
            return [_serialize_row(row) for row in rows]

    async def create_party(self, *, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO source_parties (client_id, name, scope, party_type, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                client_id,
                payload["name"],
                payload["scope"],
                payload["party_type"],
                payload.get("is_active", True),
            )
            return _serialize_row(row)

    async def update_party(self, *, party_id: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE source_parties
                SET name = COALESCE($3, name),
                    scope = COALESCE($4, scope),
                    party_type = COALESCE($5, party_type),
                    is_active = COALESCE($6, is_active),
                    updated_at = NOW()
                WHERE party_id = $1 AND client_id = $2
                RETURNING *
                """,
                uuid.UUID(party_id),
                client_id,
                payload.get("name"),
                payload.get("scope"),
                payload.get("party_type"),
                payload.get("is_active"),
            )
            return _serialize_row(row) if row else None

    async def list_rulesets(self, *, client_id: str, workflow_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.*, COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.display_order)
                    FILTER (WHERE d.rule_id IS NOT NULL), '[]'::JSONB) AS rules
                FROM rule_sets r
                LEFT JOIN rule_definitions d ON d.ruleset_id = r.ruleset_id
                WHERE r.client_id = $1 AND r.workflow_id = $2
                GROUP BY r.ruleset_id
                ORDER BY r.version DESC
                """,
                client_id,
                workflow_id,
            )
            return [_serialize_row(row) for row in rows]

    async def get_active_ruleset(self, *, client_id: str, workflow_id: str) -> dict[str, Any] | None:
        rows = await self.list_rulesets(client_id=client_id, workflow_id=workflow_id)
        return next((row for row in rows if row["status"] == "ACTIVE"), None)

    async def create_ruleset(self, *, client_id: str, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                version = int(await conn.fetchval(
                    "SELECT COALESCE(MAX(version), 0) + 1 FROM rule_sets WHERE client_id = $1 AND workflow_id = $2",
                    client_id,
                    workflow_id,
                ))
                ruleset_id = payload.get("ruleset_id") or f"{client_id}-{workflow_id}-v{version}"
                await conn.execute(
                    """
                    INSERT INTO rule_sets (ruleset_id, client_id, workflow_id, version, status, name)
                    VALUES ($1, $2, $3, $4, 'DRAFT', $5)
                    """,
                    ruleset_id, client_id, workflow_id, version, payload["name"],
                )
                for position, rule in enumerate(payload.get("rules", []), start=1):
                    await conn.execute(
                        """
                        INSERT INTO rule_definitions (
                            rule_id, ruleset_id, template_type, name, field_path,
                            authoritative_document_type, compared_document_type,
                            parameters, severity, failure_outcome, display_order, is_active
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::JSONB, $9, $10, $11, $12)
                        """,
                        rule.get("rule_id") or f"{ruleset_id}-rule-{position}", ruleset_id,
                        rule["template_type"], rule["name"], rule.get("field_path"),
                        rule.get("authoritative_document_type"), rule.get("compared_document_type"),
                        json.dumps(rule.get("parameters", {})), rule.get("severity", "warning"),
                        rule.get("failure_outcome", "REVIEW_REQUIRED"), position, rule.get("is_active", True),
                    )
        return (await self.list_rulesets(client_id=client_id, workflow_id=workflow_id))[0]

    async def activate_ruleset(self, *, ruleset_id: str, client_id: str, confirmed_by: str, comment: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                target = await conn.fetchrow(
                    "SELECT * FROM rule_sets WHERE ruleset_id = $1 AND client_id = $2 FOR UPDATE",
                    ruleset_id, client_id,
                )
                if not target or target["status"] != "DRAFT":
                    return None
                await conn.execute(
                    "UPDATE rule_sets SET status = 'RETIRED', retired_at = NOW(), updated_at = NOW() WHERE client_id = $1 AND workflow_id = $2 AND status = 'ACTIVE'",
                    client_id, target["workflow_id"],
                )
                row = await conn.fetchrow(
                    """
                    UPDATE rule_sets SET status = 'ACTIVE', confirmation_comment = $3,
                        confirmed_by = $4, activated_at = NOW(), updated_at = NOW()
                    WHERE ruleset_id = $1 AND client_id = $2 RETURNING *
                    """,
                    ruleset_id, client_id, comment, uuid.UUID(confirmed_by),
                )
                await conn.execute(
                    """
                    INSERT INTO notifications (client_id, notification_type, severity, title, message, deduplication_key)
                    VALUES ($1, 'RULESET_ACTIVATED', 'info', 'Ruleset activated', $2, $3)
                    ON CONFLICT (deduplication_key) DO NOTHING
                    """,
                    client_id, f"Ruleset {ruleset_id} is now active.", f"ruleset-activated:{ruleset_id}",
                )
                return _serialize_row(row)

    async def list_notifications(self, *, client_id: str, unread_only: bool, limit: int) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM notifications WHERE client_id = $1
                    AND ($2::BOOLEAN = FALSE OR read_at IS NULL)
                ORDER BY created_at DESC LIMIT $3
                """, client_id, unread_only, limit,
            )
            return [_serialize_row(row) for row in rows]

    async def mark_notification_read(self, *, notification_id: str, client_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE notifications SET read_at = COALESCE(read_at, NOW())
                   WHERE notification_id = $1 AND client_id = $2 RETURNING *""",
                uuid.UUID(notification_id), client_id,
            )
            return _serialize_row(row) if row else None

    async def create_case_with_sources(
        self,
        *,
        case_id: str,
        client_id: str,
        external_reference: str | None,
        workflow_id: str,
        workflow_version: str,
        sources: list[dict[str, Any]],
        intake: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO dossier_cases (
                        case_id, client_id, external_reference, workflow_id,
                        workflow_version, status, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, 'INGESTED', $6, $6)
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    external_reference,
                    workflow_id,
                    workflow_version,
                    now,
                )

                intake = intake or {}
                intake_id = await conn.fetchval(
                    """
                    INSERT INTO intake_submissions (
                        client_id, intake_channel, sender_party_id, received_at,
                        channel_reference, idempotency_key, metadata
                    ) VALUES ($1, $2, $3, COALESCE($4, NOW()), $5, $6, $7::JSONB)
                    RETURNING intake_submission_id
                    """,
                    client_id, intake.get("intake_channel", "WEB_UPLOAD"),
                    uuid.UUID(intake["sender_party_id"]) if intake.get("sender_party_id") else None,
                    intake.get("received_at"), intake.get("channel_reference"), intake.get("idempotency_key"),
                    json.dumps(intake.get("metadata", {})),
                )

                for source in sources:
                    document_id = uuid.UUID(source["document_id"])
                    job_id = uuid.UUID(source["job_id"])
                    await conn.execute(
                        """
                        INSERT INTO document_artifacts (
                            document_id, case_id, client_id, artifact_kind,
                            original_filename, storage_path, file_url, sha256, intake_submission_id,
                            issuer_party_id, provenance_status,
                            page_start, page_end, document_type, status,
                            created_at, updated_at
                        )
                        VALUES (
                            $1, $2, $3, 'SOURCE', $4, $5, $6, $7,
                            $8, $9, $10, 1, $11, 'UNKNOWN', 'PENDING', $12, $12
                        )
                        """,
                        document_id,
                        uuid.UUID(case_id),
                        client_id,
                        source["original_filename"],
                        source["storage_path"],
                        source["file_url"],
                        source["sha256"],
                        intake_id,
                        uuid.UUID(source["issuer_party_id"]) if source.get("issuer_party_id") else None,
                        source.get("provenance_status", "MISSING_BOTH"),
                        source["page_count"],
                        now,
                    )
                    await conn.execute(
                        """
                        INSERT INTO processing_jobs (
                            job_id, client_id, status, file_url, case_id,
                            document_artifact_id, workflow_id, attempt_count,
                            max_attempts, idempotency_key, created_at, updated_at
                        )
                        VALUES (
                            $1, $2, 'PENDING', $3, $4, $5, $6,
                            0, 5, $7, $8, $8
                        )
                        """,
                        job_id,
                        client_id,
                        source["file_url"],
                        uuid.UUID(case_id),
                        document_id,
                        workflow_id,
                        source["idempotency_key"],
                        now,
                    )
                    await conn.execute(
                        """
                        INSERT INTO outbox_events (
                            event_type, aggregate_id, idempotency_key, payload,
                            status, available_at, created_at
                        )
                        VALUES (
                            'DOSSIER_SOURCE_PROCESS', $1, $2, $3::JSONB,
                            'PENDING', $4, $4
                        )
                        """,
                        job_id,
                        source["idempotency_key"],
                        json.dumps(
                            {
                                "job_id": str(job_id),
                                "case_id": case_id,
                                "document_artifact_id": str(document_id),
                                "client_id": client_id,
                                "workflow_id": workflow_id,
                                "file_path": source["file_url"],
                            }
                        ),
                        now,
                    )

                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        case_id, client_id, event_type, event_data
                    )
                    VALUES ($1, $2, 'CASE_INGESTED', $3::JSONB)
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    json.dumps({"source_count": len(sources)}),
                )

        return {
            "case_id": case_id,
            "document_ids": [source["document_id"] for source in sources],
            "job_ids": [source["job_id"] for source in sources],
            "status": "INGESTED",
        }

    async def claim_outbox_events(self, *, limit: int = 20) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE outbox_events
                    SET status = 'PENDING',
                        locked_at = NULL,
                        available_at = NOW()
                    WHERE status = 'PUBLISHING'
                      AND locked_at < NOW() - INTERVAL '5 minutes'
                    """
                )
                rows = await conn.fetch(
                    """
                    SELECT *
                    FROM outbox_events
                    WHERE status = 'PENDING' AND available_at <= NOW()
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT $1
                    """,
                    limit,
                )
                if rows:
                    await conn.execute(
                        """
                        UPDATE outbox_events
                        SET status = 'PUBLISHING',
                            publish_attempts = publish_attempts + 1,
                            locked_at = NOW()
                        WHERE event_id = ANY($1::UUID[])
                        """,
                        [row["event_id"] for row in rows],
                    )
                return [_serialize_row(row) for row in rows]

    async def mark_outbox_published(self, event_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE outbox_events
                SET status = 'PUBLISHED',
                    locked_at = NULL,
                    published_at = NOW(),
                    last_error = NULL
                WHERE event_id = $1
                """,
                uuid.UUID(event_id),
            )

    async def release_outbox_event(self, event_id: str, error: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE outbox_events
                SET status = CASE WHEN publish_attempts >= 10 THEN 'FAILED' ELSE 'PENDING' END,
                    available_at = NOW() + INTERVAL '30 seconds',
                    locked_at = NULL,
                    last_error = $2
                WHERE event_id = $1
                """,
                uuid.UUID(event_id),
                error[:4000],
            )

    async def get_source_for_job(
        self,
        *,
        job_id: str,
        client_id: str,
    ) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    j.job_id, j.case_id, j.document_artifact_id, j.workflow_id,
                    j.status AS job_status, j.attempt_count, j.max_attempts,
                    d.original_filename, d.storage_path, d.file_url, d.sha256,
                    d.page_start, d.page_end, d.status AS document_status
                FROM processing_jobs j
                JOIN document_artifacts d
                  ON d.document_id = j.document_artifact_id
                WHERE j.job_id = $1 AND j.client_id = $2
                """,
                uuid.UUID(job_id),
                client_id,
            )
            return _serialize_row(row) if row else None

    async def mark_source_processing(self, *, job_id: str, client_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    UPDATE processing_jobs
                    SET status = 'PROCESSING', updated_at = NOW()
                    WHERE job_id = $1 AND client_id = $2
                    RETURNING case_id, document_artifact_id
                    """,
                    uuid.UUID(job_id),
                    client_id,
                )
                if not row:
                    raise DossierNotFoundError(job_id)
                await conn.execute(
                    """
                    UPDATE document_artifacts
                    SET status = 'PROCESSING', updated_at = NOW()
                    WHERE document_id = $1 AND client_id = $2
                    """,
                    row["document_artifact_id"],
                    client_id,
                )
                await conn.execute(
                    """
                    UPDATE dossier_cases
                    SET status = 'PROCESSING', updated_at = NOW()
                    WHERE case_id = $1 AND client_id = $2
                    """,
                    row["case_id"],
                    client_id,
                )

    async def save_source_results(
        self,
        *,
        job_id: str,
        client_id: str,
        provider_id: str,
        model_id: str,
        segments: list[dict[str, Any]],
    ) -> str:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                source = await conn.fetchrow(
                    """
                    SELECT d.*, j.case_id
                    FROM processing_jobs j
                    JOIN document_artifacts d
                      ON d.document_id = j.document_artifact_id
                    WHERE j.job_id = $1 AND j.client_id = $2
                    FOR UPDATE
                    """,
                    uuid.UUID(job_id),
                    client_id,
                )
                if not source:
                    raise DossierNotFoundError(job_id)

                await conn.execute(
                    """
                    UPDATE document_artifacts
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE source_artifact_id = $1 AND is_active = TRUE
                    """,
                    source["document_id"],
                )

                for segment in segments:
                    document_id = uuid.UUID(segment["document_id"])
                    facts = segment["facts"]
                    confidence_values = [float(fact["confidence"]) for fact in facts]
                    overall_confidence = (
                        sum(confidence_values) / len(confidence_values)
                        if confidence_values
                        else None
                    )
                    await conn.execute(
                        """
                        INSERT INTO document_artifacts (
                            document_id, case_id, client_id, source_artifact_id,
                            artifact_kind, original_filename, storage_path,
                            file_url, sha256, page_start, page_end,
                            document_type, classification_confidence,
                            status, is_active, created_at, updated_at
                        )
                        VALUES (
                            $1, $2, $3, $4, 'SEGMENT', $5, $6, $7, $8,
                            $9, $10, $11, $12, 'COMPLETED', TRUE, NOW(), NOW()
                        )
                        """,
                        document_id,
                        source["case_id"],
                        client_id,
                        source["document_id"],
                        source["original_filename"],
                        source["storage_path"],
                        source["file_url"],
                        source["sha256"],
                        segment["page_start"],
                        segment["page_end"],
                        segment["document_type"],
                        segment["classification_confidence"],
                    )
                    extraction_id = await conn.fetchval(
                        """
                        INSERT INTO extraction_results (
                            document_id, client_id, provider_id, model_id,
                            schema_version, normalized_data, overall_confidence
                        )
                        VALUES ($1, $2, $3, $4, $5, $6::JSONB, $7)
                        RETURNING extraction_id
                        """,
                        document_id,
                        client_id,
                        provider_id,
                        model_id,
                        segment["schema_version"],
                        json.dumps({"facts": facts}),
                        overall_confidence,
                    )
                    if facts:
                        await conn.executemany(
                            """
                            INSERT INTO evidence_refs (
                                extraction_id, document_id, field_path, page,
                                source_text, confidence, bbox
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7::JSONB)
                            """,
                            [
                                (
                                    extraction_id,
                                    document_id,
                                    fact["field_path"],
                                    fact["page"],
                                    fact["source_text"],
                                    fact["confidence"],
                                    json.dumps(fact.get("bbox"))
                                    if fact.get("bbox") is not None
                                    else None,
                                )
                                for fact in facts
                            ],
                        )

                await conn.execute(
                    """
                    UPDATE document_artifacts
                    SET status = 'COMPLETED', updated_at = NOW()
                    WHERE document_id = $1
                    """,
                    source["document_id"],
                )
                await conn.execute(
                    """
                    UPDATE processing_jobs
                    SET status = 'COMPLETED', error_log = NULL, updated_at = NOW()
                    WHERE job_id = $1
                    """,
                    uuid.UUID(job_id),
                )
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        case_id, client_id, event_type, event_data
                    )
                    VALUES ($1, $2, 'SOURCE_PROCESSED', $3::JSONB)
                    """,
                    source["case_id"],
                    client_id,
                    json.dumps(
                        {
                            "job_id": job_id,
                            "source_document_id": str(source["document_id"]),
                            "segment_count": len(segments),
                            "provider_id": provider_id,
                            "model_id": model_id,
                        }
                    ),
                )
                return str(source["case_id"])

    async def is_case_ready_for_decision(self, *, case_id: str, client_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            pending = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM processing_jobs
                WHERE case_id = $1
                  AND client_id = $2
                  AND status <> 'COMPLETED'
                """,
                uuid.UUID(case_id),
                client_id,
            )
            return int(pending or 0) == 0

    async def load_case_context(
        self,
        *,
        case_id: str,
        client_id: str,
    ) -> DossierCaseContext:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            case = await conn.fetchrow(
                """
                SELECT *
                FROM dossier_cases
                WHERE case_id = $1 AND client_id = $2
                """,
                uuid.UUID(case_id),
                client_id,
            )
            if not case:
                raise DossierNotFoundError(case_id)
            documents = await conn.fetch(
                """
                SELECT
                    d.document_id, d.source_artifact_id, d.original_filename,
                    d.file_url, d.sha256, d.page_start, d.page_end,
                    d.document_type, d.classification_confidence,
                    e.provider_id, e.model_id, e.schema_version,
                    e.normalized_data
                FROM document_artifacts d
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM extraction_results er
                    WHERE er.document_id = d.document_id
                    ORDER BY er.created_at DESC
                    LIMIT 1
                ) e ON TRUE
                WHERE d.case_id = $1
                  AND d.client_id = $2
                  AND d.artifact_kind = 'SEGMENT'
                  AND d.is_active = TRUE
                ORDER BY d.page_start, d.created_at
                """,
                uuid.UUID(case_id),
                client_id,
            )
            document_payloads: list[dict[str, Any]] = []
            for document in documents:
                payload = _serialize_row(document)
                normalized = payload.pop("normalized_data", None) or {}
                payload["facts"] = normalized.get("facts", [])
                document_payloads.append(payload)

            return DossierCaseContext(
                case_id=case_id,
                client_id=client_id,
                external_reference=case["external_reference"],
                documents=document_payloads,
            )

    async def save_decision(
        self,
        *,
        case_context: DossierCaseContext,
        decision: DossierDecision,
        report_payload: dict[str, Any],
    ) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                case = await conn.fetchrow(
                    """
                    SELECT *
                    FROM dossier_cases
                    WHERE case_id = $1 AND client_id = $2
                    FOR UPDATE
                    """,
                    uuid.UUID(case_context.case_id),
                    case_context.client_id,
                )
                if not case:
                    raise DossierNotFoundError(case_context.case_id)
                if case["status"] != "PROCESSING":
                    current_version = await conn.fetchval(
                        """
                        SELECT MAX(decision_version)
                        FROM decision_results
                        WHERE case_id = $1
                        """,
                        uuid.UUID(case_context.case_id),
                    )
                    return int(current_version or 0)

                decision_version = int(
                    await conn.fetchval(
                        """
                        SELECT COALESCE(MAX(decision_version), 0) + 1
                        FROM decision_results
                        WHERE case_id = $1
                        """,
                        uuid.UUID(case_context.case_id),
                    )
                )
                decision_id = await conn.fetchval(
                    """
                    INSERT INTO decision_results (
                        case_id, client_id, decision_version, status,
                        ruleset_id, ruleset_version, summary,
                        discrepancies, report_payload
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8::JSONB, $9::JSONB
                    )
                    RETURNING decision_id
                    """,
                    uuid.UUID(case_context.case_id),
                    case_context.client_id,
                    decision_version,
                    decision.status.value,
                    decision.ruleset_id,
                    decision.ruleset_version,
                    decision.summary,
                    json.dumps(
                        [item.model_dump(mode="json") for item in decision.discrepancies]
                    ),
                    json.dumps(report_payload),
                )
                await conn.execute(
                    """
                    UPDATE review_tasks
                    SET status = 'CANCELLED'
                    WHERE case_id = $1 AND status = 'PENDING'
                    """,
                    uuid.UUID(case_context.case_id),
                )
                await conn.execute(
                    """
                    INSERT INTO review_tasks (
                        case_id, decision_id, client_id, status
                    )
                    VALUES ($1, $2, $3, 'PENDING')
                    """,
                    uuid.UUID(case_context.case_id),
                    decision_id,
                    case_context.client_id,
                )
                await conn.execute(
                    """
                    UPDATE dossier_cases
                    SET status = 'AWAITING_REVIEW', updated_at = NOW()
                    WHERE case_id = $1
                    """,
                    uuid.UUID(case_context.case_id),
                )
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        case_id, client_id, event_type, event_data
                    )
                    VALUES ($1, $2, 'DECISION_GENERATED', $3::JSONB)
                    """,
                    uuid.UUID(case_context.case_id),
                    case_context.client_id,
                    json.dumps(
                        {
                            "decision_id": str(decision_id),
                            "decision_version": decision_version,
                            "status": decision.status.value,
                        }
                    ),
                )
                notification_type = (
                    "DOSSIER_BLOCKED"
                    if decision.status.value == "BLOCKED"
                    else "DOSSIER_REVIEW_REQUIRED"
                )
                await conn.execute(
                    """
                    INSERT INTO notifications (
                        client_id, case_id, notification_type, severity, title,
                        message, payload, deduplication_key
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7::JSONB, $8)
                    ON CONFLICT (deduplication_key) DO NOTHING
                    """,
                    case_context.client_id,
                    uuid.UUID(case_context.case_id),
                    notification_type,
                    "critical" if decision.status.value == "BLOCKED" else "warning",
                    "Dossier blocked" if decision.status.value == "BLOCKED" else "Dossier review required",
                    decision.summary,
                    json.dumps({"decision_id": str(decision_id), "decision_version": decision_version}),
                    f"decision:{decision_id}",
                )
                return decision_version

    async def schedule_retry(
        self,
        *,
        job_id: str,
        client_id: str,
        error: str,
    ) -> bool:
        retry_delays = (30, 120, 600, 600, 600)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                job = await conn.fetchrow(
                    """
                    SELECT *
                    FROM processing_jobs
                    WHERE job_id = $1 AND client_id = $2
                    FOR UPDATE
                    """,
                    uuid.UUID(job_id),
                    client_id,
                )
                if not job:
                    raise DossierNotFoundError(job_id)
                next_attempt = int(job["attempt_count"]) + 1
                if next_attempt >= int(job["max_attempts"]):
                    await self._mark_failed_in_transaction(
                        conn=conn,
                        job=job,
                        client_id=client_id,
                        error=error,
                    )
                    return False

                delay = retry_delays[min(next_attempt - 1, len(retry_delays) - 1)]
                available_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                await conn.execute(
                    """
                    UPDATE processing_jobs
                    SET status = 'PENDING', attempt_count = $2,
                        error_log = $3, updated_at = NOW()
                    WHERE job_id = $1
                    """,
                    uuid.UUID(job_id),
                    next_attempt,
                    error[:4000],
                )
                await conn.execute(
                    """
                    UPDATE document_artifacts
                    SET status = 'PENDING', updated_at = NOW()
                    WHERE document_id = $1
                    """,
                    job["document_artifact_id"],
                )
                payload = {
                    "job_id": job_id,
                    "case_id": str(job["case_id"]),
                    "document_artifact_id": str(job["document_artifact_id"]),
                    "client_id": client_id,
                    "workflow_id": job["workflow_id"],
                    "file_path": job["file_url"],
                }
                await conn.execute(
                    """
                    INSERT INTO outbox_events (
                        event_type, aggregate_id, idempotency_key, payload,
                        status, available_at
                    )
                    VALUES (
                        'DOSSIER_SOURCE_PROCESS', $1, $2, $3::JSONB,
                        'PENDING', $4
                    )
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    uuid.UUID(job_id),
                    f"job:{job_id}:attempt:{next_attempt}",
                    json.dumps(payload),
                    available_at,
                )
                return True

    async def mark_job_failed(
        self,
        *,
        job_id: str,
        client_id: str,
        error: str,
    ) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                job = await conn.fetchrow(
                    """
                    SELECT *
                    FROM processing_jobs
                    WHERE job_id = $1 AND client_id = $2
                    FOR UPDATE
                    """,
                    uuid.UUID(job_id),
                    client_id,
                )
                if not job:
                    raise DossierNotFoundError(job_id)
                await self._mark_failed_in_transaction(
                    conn=conn,
                    job=job,
                    client_id=client_id,
                    error=error,
                )

    async def _mark_failed_in_transaction(
        self,
        *,
        conn: asyncpg.Connection,
        job: asyncpg.Record,
        client_id: str,
        error: str,
    ) -> None:
        await conn.execute(
            """
            UPDATE processing_jobs
            SET status = 'FAILED', error_log = $2, updated_at = NOW()
            WHERE case_id = $1
              AND status <> 'COMPLETED'
            """,
            job["case_id"],
            error[:4000],
        )
        await conn.execute(
            """
            UPDATE document_artifacts
            SET status = 'FAILED', updated_at = NOW()
            WHERE case_id = $1
              AND artifact_kind = 'SOURCE'
              AND status <> 'COMPLETED'
            """,
            job["case_id"],
        )
        await conn.execute(
            """
            UPDATE dossier_cases
            SET status = 'FAILED', updated_at = NOW()
            WHERE case_id = $1
            """,
            job["case_id"],
        )
        await conn.execute(
            """
            INSERT INTO audit_events (
                case_id, client_id, event_type, event_data
            )
            VALUES ($1, $2, 'PROCESSING_FAILED', $3::JSONB)
            """,
            job["case_id"],
            client_id,
            json.dumps({"job_id": str(job["job_id"]), "error": error[:4000]}),
        )
        await conn.execute(
            """
            INSERT INTO notifications (
                client_id, case_id, notification_type, severity, title,
                message, payload, deduplication_key
            ) VALUES ($1, $2, 'PROCESSING_FAILED', 'critical', 'Dossier processing failed', $3, $4::JSONB, $5)
            ON CONFLICT (deduplication_key) DO NOTHING
            """,
            client_id,
            job["case_id"],
            error[:4000],
            json.dumps({"job_id": str(job["job_id"])}),
            f"processing-failed:{job['job_id']}",
        )

    async def list_cases(
        self,
        *,
        client_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.*,
                    d.status AS decision_status,
                    d.decision_version,
                    (
                        SELECT COUNT(*)
                        FROM document_artifacts a
                        WHERE a.case_id = c.case_id
                          AND a.artifact_kind = 'SOURCE'
                    ) AS source_count
                FROM dossier_cases c
                LEFT JOIN LATERAL (
                    SELECT status, decision_version
                    FROM decision_results dr
                    WHERE dr.case_id = c.case_id
                    ORDER BY decision_version DESC
                    LIMIT 1
                ) d ON TRUE
                WHERE c.client_id = $1
                  AND ($2::TEXT IS NULL OR c.status = $2)
                ORDER BY c.created_at DESC
                LIMIT $3 OFFSET $4
                """,
                client_id,
                status,
                limit,
                offset,
            )
            return [_serialize_row(row) for row in rows]

    async def get_case(self, *, case_id: str, client_id: str) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            case = await conn.fetchrow(
                """
                SELECT *
                FROM dossier_cases
                WHERE case_id = $1 AND client_id = $2
                """,
                uuid.UUID(case_id),
                client_id,
            )
            if not case:
                return None
            sources = await conn.fetch(
                """
                SELECT d.*, i.intake_channel, i.channel_reference, i.received_at,
                       sender.name AS sender_party_name, sender.scope AS sender_party_scope,
                       issuer.name AS issuer_party_name, issuer.scope AS issuer_party_scope
                FROM document_artifacts d
                LEFT JOIN intake_submissions i ON i.intake_submission_id = d.intake_submission_id
                LEFT JOIN source_parties sender ON sender.party_id = i.sender_party_id
                LEFT JOIN source_parties issuer ON issuer.party_id = d.issuer_party_id
                WHERE d.case_id = $1 AND d.client_id = $2
                  AND d.artifact_kind = 'SOURCE'
                ORDER BY d.created_at
                """,
                uuid.UUID(case_id),
                client_id,
            )
            context = await self.load_case_context(case_id=case_id, client_id=client_id)
            decision = await conn.fetchrow(
                """
                SELECT *
                FROM decision_results
                WHERE case_id = $1 AND client_id = $2
                ORDER BY decision_version DESC
                LIMIT 1
                """,
                uuid.UUID(case_id),
                client_id,
            )
            reviews = await conn.fetch(
                """
                SELECT *
                FROM review_tasks
                WHERE case_id = $1 AND client_id = $2
                ORDER BY created_at
                """,
                uuid.UUID(case_id),
                client_id,
            )
            events = await conn.fetch(
                """
                SELECT *
                FROM audit_events
                WHERE case_id = $1 AND client_id = $2
                ORDER BY created_at
                """,
                uuid.UUID(case_id),
                client_id,
            )
            return {
                "case": _serialize_row(case),
                "sources": [_serialize_row(source) for source in sources],
                "documents": context.documents,
                "decision": _serialize_row(decision) if decision else None,
                "reviews": [_serialize_row(review) for review in reviews],
                "audit_events": [_serialize_row(event) for event in events],
            }

    async def resolve_review(
        self,
        *,
        case_id: str,
        client_id: str,
        action: str,
        comment: str,
        expected_decision_version: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        resolution = ReviewResolution(
            {
                "APPROVE": "APPROVED",
                "REJECT": "REJECTED",
                "OVERRIDE": "OVERRIDDEN",
            }[action]
        )
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    """
                    SELECT *
                    FROM review_tasks
                    WHERE case_id = $1 AND client_id = $2
                      AND idempotency_key = $3
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    idempotency_key,
                )
                if existing:
                    return _serialize_row(existing)

                decision = await conn.fetchrow(
                    """
                    SELECT *
                    FROM decision_results
                    WHERE case_id = $1 AND client_id = $2
                    ORDER BY decision_version DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    uuid.UUID(case_id),
                    client_id,
                )
                if not decision:
                    raise DossierNotFoundError(case_id)
                if int(decision["decision_version"]) != expected_decision_version:
                    raise DecisionVersionConflictError(
                        f"Expected decision version {expected_decision_version}, "
                        f"current version is {decision['decision_version']}"
                    )
                if action == "APPROVE" and decision["status"] != "READY":
                    raise InvalidReviewResolutionError(
                        "Only a READY decision can be approved; use OVERRIDE with a reason"
                    )

                review = await conn.fetchrow(
                    """
                    UPDATE review_tasks
                    SET status = 'RESOLVED', resolution = $4, comment = $5,
                        idempotency_key = $6, resolved_at = NOW()
                    WHERE case_id = $1 AND client_id = $2
                      AND decision_id = $3 AND status = 'PENDING'
                    RETURNING *
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    decision["decision_id"],
                    resolution.value,
                    comment,
                    idempotency_key,
                )
                if not review:
                    raise InvalidReviewResolutionError("No pending review exists for this decision")
                await conn.execute(
                    """
                    UPDATE dossier_cases
                    SET status = 'RESOLVED', updated_at = NOW()
                    WHERE case_id = $1
                    """,
                    uuid.UUID(case_id),
                )
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        case_id, client_id, event_type, event_data
                    )
                    VALUES ($1, $2, 'REVIEW_RESOLVED', $3::JSONB)
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    json.dumps(
                        {
                            "decision_id": str(decision["decision_id"]),
                            "decision_version": decision["decision_version"],
                            "resolution": resolution.value,
                            "comment": comment,
                        }
                    ),
                )
                return _serialize_row(review)

    async def reprocess_sources(
        self,
        *,
        case_id: str,
        client_id: str,
        document_ids: list[str],
        reason: str,
    ) -> list[str]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                case = await conn.fetchrow(
                    """
                    SELECT *
                    FROM dossier_cases
                    WHERE case_id = $1 AND client_id = $2
                    FOR UPDATE
                    """,
                    uuid.UUID(case_id),
                    client_id,
                )
                if not case:
                    raise DossierNotFoundError(case_id)
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT COALESCE(source_artifact_id, document_id) AS source_id
                    FROM document_artifacts
                    WHERE case_id = $1 AND client_id = $2
                      AND document_id = ANY($3::UUID[])
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    [uuid.UUID(document_id) for document_id in document_ids],
                )
                if not rows:
                    raise DossierNotFoundError("No requested documents belong to this case")

                job_ids: list[str] = []
                for row in rows:
                    source = await conn.fetchrow(
                        """
                        SELECT *
                        FROM document_artifacts
                        WHERE document_id = $1 AND artifact_kind = 'SOURCE'
                        """,
                        row["source_id"],
                    )
                    if not source:
                        continue
                    job_id = uuid.uuid4()
                    idempotency_key = f"reprocess:{case_id}:{source['document_id']}:{job_id}"
                    await conn.execute(
                        """
                        INSERT INTO processing_jobs (
                            job_id, client_id, status, file_url, case_id,
                            document_artifact_id, workflow_id, attempt_count,
                            max_attempts, idempotency_key, created_at, updated_at
                        )
                        VALUES (
                            $1, $2, 'PENDING', $3, $4, $5, $6,
                            0, 5, $7, NOW(), NOW()
                        )
                        """,
                        job_id,
                        client_id,
                        source["file_url"],
                        uuid.UUID(case_id),
                        source["document_id"],
                        case["workflow_id"],
                        idempotency_key,
                    )
                    await conn.execute(
                        """
                        INSERT INTO outbox_events (
                            event_type, aggregate_id, idempotency_key, payload
                        )
                        VALUES (
                            'DOSSIER_SOURCE_PROCESS', $1, $2, $3::JSONB
                        )
                        """,
                        job_id,
                        idempotency_key,
                        json.dumps(
                            {
                                "job_id": str(job_id),
                                "case_id": case_id,
                                "document_artifact_id": str(source["document_id"]),
                                "client_id": client_id,
                                "workflow_id": case["workflow_id"],
                                "file_path": source["file_url"],
                            }
                        ),
                    )
                    await conn.execute(
                        """
                        UPDATE document_artifacts
                        SET status = 'PENDING', updated_at = NOW()
                        WHERE document_id = $1
                        """,
                        source["document_id"],
                    )
                    job_ids.append(str(job_id))

                await conn.execute(
                    """
                    UPDATE review_tasks
                    SET status = 'CANCELLED'
                    WHERE case_id = $1 AND status = 'PENDING'
                    """,
                    uuid.UUID(case_id),
                )
                await conn.execute(
                    """
                    UPDATE dossier_cases
                    SET status = 'PROCESSING', updated_at = NOW()
                    WHERE case_id = $1
                    """,
                    uuid.UUID(case_id),
                )
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        case_id, client_id, event_type, event_data
                    )
                    VALUES ($1, $2, 'REPROCESS_REQUESTED', $3::JSONB)
                    """,
                    uuid.UUID(case_id),
                    client_id,
                    json.dumps({"reason": reason, "job_ids": job_ids}),
                )
                return job_ids
