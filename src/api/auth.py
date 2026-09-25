from __future__ import annotations

from typing import Any

import httpx
from fastapi import Header, HTTPException

from src.config import get_settings
from src.infrastructure.dossier_repos import DossierRepository


async def require_super_admin(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Validate a Supabase Auth access token, then require the configured platform role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication is required")

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication is required")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Authentication provider unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = response.json()
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authenticated user")

    repository = DossierRepository(settings.database_url or "")
    if not await repository.is_platform_super_admin(user_id):
        raise HTTPException(status_code=403, detail="Platform super-admin access is required")
    return user
