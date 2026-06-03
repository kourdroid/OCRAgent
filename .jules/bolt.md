## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2025-06-03 - [Supply Chain String Normalization Optimization]
**Learning:** In `src/plugins/supply_chain.py`, string normalization was heavily repeated during O(N*M) 3-way matching comparisons. Using `re.compile` prevents compiling on every function call, and `@functools.lru_cache` provides a significant 8x speedup for pure functions repeatedly transforming similar strings. Ensure variables passed to the cache are hashable (like `str`).
**Action:** Always look for O(N*M) loops comparing normalized strings and apply memoization to the normalization helper functions.
