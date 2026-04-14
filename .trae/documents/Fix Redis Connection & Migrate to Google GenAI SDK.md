# Fix Plan: Redis Connection & Google GenAI Migration

I have identified the root causes for both the Redis crash and the Google GenAI warning.

## 1. Redis Connection Crash (`[Errno 111] Connect call failed`)
**Cause:** The worker container is inheriting `REDIS_URL=redis://localhost:6379/0` from your local `.env` file. Inside Docker, `localhost` refers to the container itself, not the Redis service.
**Fix:** Explicitly override `REDIS_URL` in `docker-compose.yml` to use the internal Docker hostname `redis` (e.g., `redis://redis:6379/0`).

## 2. Google GenAI Deprecation (`FutureWarning`)
**Cause:** The project uses the deprecated `google-generativeai` package.
**Fix:** Migrate to the new official `google-genai` SDK (v1.0+).
**Changes:**
*   Update `requirements.txt`: `google-generativeai` -> `google-genai`
*   Refactor `src/core/nodes.py`:
    *   Use `from google import genai`
    *   Use `client.aio.models.generate_content`
    *   Leverage native Pydantic support in `response_schema` (simplifying schema handling).

## Execution Steps
1.  **Modify `docker-compose.yml`**: Hardcode internal Redis URL for services.
2.  **Update `requirements.txt`**: Switch SDK versions.
3.  **Refactor `src/core/nodes.py`**: Implement new SDK logic.
4.  **Rebuild**: You will need to run `docker-compose up --build` after these changes.
