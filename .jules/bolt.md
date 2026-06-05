## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-06-05 - [3-Way Match String Normalization Redundancy]
**Learning:** The `_normalize_description` function in `src/plugins/supply_chain.py` is called inside nested loops comparing N invoice items to M PO/receipt items, causing O(N*M) redundant regex computations and string operations for the same descriptions.
**Action:** Pre-compile the regex and use `@functools.lru_cache` on a string-only helper function to cache normalization results. Always cast inputs to hashable types (like `str`) before caching to avoid `TypeError: unhashable type`.
