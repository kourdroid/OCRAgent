## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2026-07-10 - [Database Index for Pagination]
**Learning:** The `GET /jobs` endpoint in `src/api/routes.py` performs an `ORDER BY created_at DESC` query with optional `WHERE status = $1` filtering. Without indexes, PostgreSQL executes expensive O(N log N) full-table sorts on the `processing_jobs` table.
**Action:** Add B-Tree indexes on `(status, created_at DESC)` and `(created_at DESC)` using `CREATE INDEX CONCURRENTLY` to optimize these queries to O(LIMIT) backwards index scans without blocking production writes.
