## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [HTTP Connection Pooling for Concurrent Uploads]
**Learning:** Using `asyncio.gather` for concurrent I/O isn't fully optimized if the underlying HTTP client (like `httpx.AsyncClient`) is instantiated inside the sub-task. This causes repeated TCP/TLS handshakes, negating some concurrency benefits.
**Action:** When performing concurrent HTTP requests (e.g., uploading many files), instantiate a shared `httpx.AsyncClient` outside the loop/task generation using an `async with` block, and pass the client into the concurrent sub-tasks to take advantage of HTTP connection pooling.
## 2025-02-23 - Database Connection Pooling Overhead
 **Learning:** Instantiating raw `asyncpg.connect()` connections inside high-frequency application routes (like `/health`) introduces significant TCP/TLS handshake latency, which can bottleneck application responsiveness and exhaust database connection limits.
 **Action:** Always use shared application connection pools (`get_connection_pool`) for route handlers and acquire connections from the pool (`async with pool.acquire() as conn:`) instead of spinning up isolated connections per request.
## 2024-05-18 - [Regex Optimization in Repetitive Functions]
**Learning:** Functions that parse strings using regular expressions on every invocation (like `_extract_po_number`) incur performance penalties if they use `re.search` directly with raw strings, as it causes repeated regex compilation/cache lookups.
**Action:** Pre-compile regular expressions at the module level using `re.compile()` to improve performance and avoid redundant parsing.

## 2024-05-18 - [Database Connections in Standalone Scripts]
**Learning:** Using a shared application connection pool (e.g., `get_connection_pool`) is an anti-pattern for short-lived, standalone healthcheck scripts, because they cannot actually share the pool with the main process. This introduces unnecessary overhead and risks resource leaks if the pool is not explicitly closed.
**Action:** For standalone scripts like `src/worker/healthcheck.py`, use simple, direct connections (`asyncpg.connect()`) instead of a connection pool.
