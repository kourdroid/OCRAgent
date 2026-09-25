from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_super_admin
from src.api.dossier_routes import _require_database_url, _require_dossier_client
from src.dossiers.models import (
    PartyCreateRequest,
    PartyUpdateRequest,
    RuleSetActivationRequest,
    RuleSetCreateRequest,
)
from src.infrastructure.dossier_repos import DossierRepository

router = APIRouter(
    prefix="/admin",
    tags=["administration"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("/parties")
async def list_parties(
    client_id: str = Query(default="delassus"),
    active_only: bool = Query(default=False),
) -> list[dict[str, Any]]:
    normalized, _, _ = _require_dossier_client(client_id)
    return await DossierRepository(_require_database_url()).list_parties(
        client_id=normalized, active_only=active_only
    )


@router.post("/parties", status_code=201)
async def create_party(
    payload: PartyCreateRequest,
    client_id: str = Query(default="delassus"),
) -> dict[str, Any]:
    normalized, _, _ = _require_dossier_client(client_id)
    try:
        return await DossierRepository(_require_database_url()).create_party(
            client_id=normalized, payload=payload.model_dump(mode="json")
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail="A party with this name already exists") from exc


@router.patch("/parties/{party_id}")
async def update_party(
    party_id: str,
    payload: PartyUpdateRequest,
    client_id: str = Query(default="delassus"),
) -> dict[str, Any]:
    normalized, _, _ = _require_dossier_client(client_id)
    result = await DossierRepository(_require_database_url()).update_party(
        party_id=party_id,
        client_id=normalized,
        payload=payload.model_dump(exclude_unset=True, mode="json"),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Party not found")
    return result


@router.get("/rule-sets")
async def list_rule_sets(
    client_id: str = Query(default="delassus"),
) -> list[dict[str, Any]]:
    normalized, config, _ = _require_dossier_client(client_id)
    return await DossierRepository(_require_database_url()).list_rulesets(
        client_id=normalized, workflow_id=config.workflow_id
    )


@router.post("/rule-sets", status_code=201)
async def create_rule_set(
    payload: RuleSetCreateRequest,
    client_id: str = Query(default="delassus"),
) -> dict[str, Any]:
    normalized, config, _ = _require_dossier_client(client_id)
    return await DossierRepository(_require_database_url()).create_ruleset(
        client_id=normalized,
        workflow_id=config.workflow_id,
        payload=payload.model_dump(mode="json"),
    )


@router.post("/rule-sets/{ruleset_id}/activate")
async def activate_rule_set(
    ruleset_id: str,
    payload: RuleSetActivationRequest,
    user: dict[str, Any] = Depends(require_super_admin),
) -> dict[str, Any]:
    normalized, _, _ = _require_dossier_client(payload.client_id)
    result = await DossierRepository(_require_database_url()).activate_ruleset(
        ruleset_id=ruleset_id,
        client_id=normalized,
        confirmed_by=user["id"],
        comment=payload.confirmation_comment,
    )
    if not result:
        raise HTTPException(status_code=409, detail="Only a draft ruleset can be activated")
    return result


@router.get("/notifications")
async def list_notifications(
    client_id: str = Query(default="delassus"),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    normalized, _, _ = _require_dossier_client(client_id)
    return await DossierRepository(_require_database_url()).list_notifications(
        client_id=normalized, unread_only=unread_only, limit=limit
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    client_id: str = Query(default="delassus"),
) -> dict[str, Any]:
    normalized, _, _ = _require_dossier_client(client_id)
    result = await DossierRepository(_require_database_url()).mark_notification_read(
        notification_id=notification_id, client_id=normalized
    )
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result
