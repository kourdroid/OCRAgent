from __future__ import annotations

import httpx


class SupabaseStorage:
    BUCKET = "ironclad-docs"

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        *,
        timeout_s: float = 60.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.timeout = httpx.Timeout(timeout_s, connect=min(timeout_s, 30.0))
        self.headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    async def upload(
        self, path: str, data: bytes, content_type: str = "application/pdf", client: httpx.AsyncClient | None = None
    ) -> str:
        """Upload file, return public URL."""
        url = f"{self.supabase_url}/storage/v1/object/{self.BUCKET}/{path}"

        if client:
            resp = await client.post(
                url,
                content=data,
                headers={**self.headers, "Content-Type": content_type},
            )
            resp.raise_for_status()
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as new_client:
                resp = await new_client.post(
                    url,
                    content=data,
                    headers={**self.headers, "Content-Type": content_type},
                )
                resp.raise_for_status()

        return self.get_public_url(path)

    async def download(self, path: str, client: httpx.AsyncClient | None = None) -> bytes:
        """Download file bytes."""
        url = f"{self.supabase_url}/storage/v1/object/{self.BUCKET}/{path}"
        if client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.content
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as new_client:
                resp = await new_client.get(url, headers=self.headers)
                resp.raise_for_status()
                return resp.content

    def get_public_url(self, path: str) -> str:
        """Construct the public URL without an API call."""
        return f"{self.supabase_url}/storage/v1/object/public/{self.BUCKET}/{path}"
