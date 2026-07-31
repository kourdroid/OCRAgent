## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [HTTP Connection Pooling for Concurrent Uploads]
**Learning:** Using `asyncio.gather` for concurrent I/O isn't fully optimized if the underlying HTTP client (like `httpx.AsyncClient`) is instantiated inside the sub-task. This causes repeated TCP/TLS handshakes, negating some concurrency benefits.
**Action:** When performing concurrent HTTP requests (e.g., uploading many files), instantiate a shared `httpx.AsyncClient` outside the loop/task generation using an `async with` block, and pass the client into the concurrent sub-tasks to take advantage of HTTP connection pooling.
## 2025-02-05 - Optimize _sanitize_for_match in _node_fingerprint_and_lookup
**Learning:** Found that `_sanitize_for_match` uses regex substitution heavily and is called for every existing `ocr_text_cache` in `registry_rows` on each document ingestion. However, these cached string values are static schema components pulled directly from the database. Re-evaluating the regex substitutions on identical text thousands of times per day is highly inefficient.
**Action:** Always ensure that pure functions operating on static reference data inside busy loops or traversal operations are aggressively memoized (`@functools.lru_cache`). I've wrapped `_sanitize_for_match` with `lru_cache(maxsize=1024)`.
