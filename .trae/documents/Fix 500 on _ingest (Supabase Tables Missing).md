## What the error means
- Your `/ingest` request is failing inside Supabase with `PGRST205`:
  - `Could not find the table 'public.processing_jobs' in the schema cache`
- So FastAPI returns `500 Internal Server Error` when it tries to insert the job row in [supabase_repos.py](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/src/infrastructure/supabase_repos.py).

## Root cause
- The Supabase project you’re pointing to does not currently expose the tables `public.processing_jobs` and `public.document_registry` via PostgREST.
- This usually happens when:
  - The SQL migration wasn’t executed in that Supabase project, or
  - It was executed in a different schema / different project, or
  - PostgREST schema cache hasn’t refreshed yet.

## Fix steps (no code changes)
1. Run the SQL in [001_registry_jobs.sql](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/sql/001_registry_jobs.sql) in the **same Supabase project** as your `SUPABASE_URL`.
2. Wait ~10–60 seconds for schema cache refresh.
3. If it still errors, restart Supabase API / PostgREST (or use Supabase “Reload schema”).

## Hardening (code changes so you don’t see “mystery 500s”)
1. Update [routes.py](file:///c:/Users/kourd/Desktop/Projects/ultimateOCR/Ironclad-OCR/src/api/routes.py) to catch `postgrest.exceptions.APIError`:
   - If `code == PGRST205`, return HTTP 503 with a clear message: “Supabase tables missing: run sql/001_registry_jobs.sql and wait for schema cache refresh”.
2. Add a `/health` endpoint that checks:
   - Supabase can `select 1` from both tables
   - Redis reachable
   - Returns a structured JSON report

## Verification
1. Re-run the same curl upload and confirm you get `{"job_id": "..."}`.
2. Confirm worker consumes from Redis stream and job row exists in Supabase.
