## Root Cause (Why it’s still connecting to localhost)
- In Docker Compose, the `worker` service still uses `REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}`.
- Your project-level `.env` contains `REDIS_URL=redis://localhost:6379/0`.
- Compose substitutes that value, so **inside the worker container it becomes `redis://localhost:6379/0`**, which points to the worker container itself (not the Redis service), causing `Errno 111`.

## Fix
1. Update `docker-compose.yml` so **worker** uses a fixed internal hostname:
   - Change `worker.environment.REDIS_URL` to `redis://redis:6379/0` (same as `api` already).

## Verification
1. Recreate containers so the new environment is applied:
   - `docker compose down`
   - `docker compose up --build`
2. Confirm logs:
   - Worker should no longer show `connecting to localhost:6379`.

## Optional Hardening (prevents this class of bug)
- Keep `.env` for local runs (`localhost`) but do not reference `${REDIS_URL}` inside compose.
- (Alternative) introduce `.env.docker` with `REDIS_URL=redis://redis:6379/0` and set `env_file:` in compose.
