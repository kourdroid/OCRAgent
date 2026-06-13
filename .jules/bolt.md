## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Supply Chain String Normalization Optimization]
**Learning:** String normalization during 3-way matching in `src/plugins/supply_chain.py` uses redundant O(N*M) computations resulting in 8.6+ seconds execution time on large document payloads due to unhashable type issues in the original `lru_cache` attempt.
**Action:** Extract string processing to a separate inner function `_normalize_string` accepting only `str` with an explicit `@functools.lru_cache` and pre-compile the matching regex to drastically reduce redundant execution time (down to < 3 seconds).
