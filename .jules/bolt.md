## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [HTTP Connection Pooling for Concurrent Uploads]
**Learning:** Using `asyncio.gather` for concurrent I/O isn't fully optimized if the underlying HTTP client (like `httpx.AsyncClient`) is instantiated inside the sub-task. This causes repeated TCP/TLS handshakes, negating some concurrency benefits.
**Action:** When performing concurrent HTTP requests (e.g., uploading many files), instantiate a shared `httpx.AsyncClient` outside the loop/task generation using an `async with` block, and pass the client into the concurrent sub-tasks to take advantage of HTTP connection pooling.
## 2024-05-18 - [Optimization] Cache `_sanitize_for_match` string normalization
**Learning:** Functions doing regex replacements in loops (like string normalization for text matching) can be a significant bottleneck.
**Action:** When a function performs heavily repetitive operations and is called frequently on the same arguments inside loops, use `@functools.lru_cache` to cache its output for significant speedups.
