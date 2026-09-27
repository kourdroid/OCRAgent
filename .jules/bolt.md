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
## 2025-02-23 - [LRU Caching Regex Operations in High-Frequency String Parsing]
 **Learning:** Repetitive string sanitation that relies on multiple regex compilations or substitutions (like `_sanitize_for_match` using `re.sub`) can become a severe CPU bottleneck when executed within large loops (e.g., comparing a string against thousands of `registry_rows`).
 **Action:** Apply `@functools.lru_cache` to small, pure string manipulation functions that are called frequently in loops, to bypass the CPU overhead of repeated regex execution for duplicate text values.
