## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2026-07-13 - [Shared HTTP Client Context]
**Learning:** Instantiating a new `httpx.AsyncClient` per request inside concurrent tasks (like `asyncio.gather`) incurs significant TCP/TLS handshake overhead. Attempting to store an `httpx.AsyncClient` on a request-scoped class instance via `__aenter__` can lead to race conditions if not careful.
**Action:** When making concurrent HTTP requests, instantiate an `httpx.AsyncClient` using an `async with` block surrounding the iteration logic and pass the shared `client` instance down into the service method to avoid handshake overhead and global state mutation.
