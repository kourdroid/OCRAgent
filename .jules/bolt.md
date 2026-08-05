## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [HTTP Connection Pooling for Concurrent Uploads]
**Learning:** Using `asyncio.gather` for concurrent I/O isn't fully optimized if the underlying HTTP client (like `httpx.AsyncClient`) is instantiated inside the sub-task. This causes repeated TCP/TLS handshakes, negating some concurrency benefits.
**Action:** When performing concurrent HTTP requests (e.g., uploading many files), instantiate a shared `httpx.AsyncClient` outside the loop/task generation using an `async with` block, and pass the client into the concurrent sub-tasks to take advantage of HTTP connection pooling.

## 2024-05-18 - [Async Mocks for LangGraph Nodes]
**Learning:** When mocking asynchronous I/O functions (like `_load_document`) within LangGraph node tests, the mock function *must* be an `async def`. A synchronous lambda returning a dummy object (e.g., `lambda _p: object()`) will cause an `await` failure (`TypeError: object object can't be used in 'await' expression`) when the LangGraph runner attempts to execute the node.
**Action:** When updating a synchronous function to be asynchronous, remember to update any unit tests that mock it using `monkeypatch.setattr` to ensure the mock is an asynchronous function or returns an awaitable.
