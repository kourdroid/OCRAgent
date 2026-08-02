## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [HTTP Connection Pooling for Concurrent Uploads]
**Learning:** Using `asyncio.gather` for concurrent I/O isn't fully optimized if the underlying HTTP client (like `httpx.AsyncClient`) is instantiated inside the sub-task. This causes repeated TCP/TLS handshakes, negating some concurrency benefits.
**Action:** When performing concurrent HTTP requests (e.g., uploading many files), instantiate a shared `httpx.AsyncClient` outside the loop/task generation using an `async with` block, and pass the client into the concurrent sub-tasks to take advantage of HTTP connection pooling.
## 2024-08-02 - [LRU Cache for _sanitize_for_match in Graph Processing]
 **Learning:** In high-frequency text processing operations, particularly during iterative database lookups for schemas in `src/core/graph.py`'s `_node_fingerprint_and_lookup`, regex matching and repetitive string manipulation operations without caching can significantly increase CPU overhead. We noticed a substantial 10x improvement (0.2174s -> 0.0246s over 300 items * 100 iterations) when applying `@functools.lru_cache(maxsize=1024)` to `_sanitize_for_match`.
 **Action:** For performance optimization in frequently called text sanitization or matching functions, apply memoization using `@functools.lru_cache` if the input space is relatively bounded.
