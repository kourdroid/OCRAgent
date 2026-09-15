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
## 2025-02-23 - [Blocking I/O in Async LangGraph Nodes]
**Learning:** Calling synchronous blocking I/O functions like `httpx.get` or standard `open()` inside asynchronous node functions (like those in `src/core/graph.py`) prevents the event loop from yielding during waits, reducing concurrency and stalling the overall pipeline.
**Action:** When a function called within an async execution context performs network or file operations (like `_load_document`), refactor it to be asynchronous using non-blocking primitives like `httpx.AsyncClient` and `aiofiles`. Ensure all upstream callers `await` the function and update any corresponding tests to mock an async function.
