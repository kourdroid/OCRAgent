## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2026-06-07 - [Memoize 3-Way Match String Normalization]
**Learning:** String normalization in `execute_3_way_match` runs O(N*M) times, where N is invoice items and M is candidate PO/receipt lines.
**Action:** Extract the non-alphanumeric regex compilation out of the function, create a dedicated helper for string manipulation, and apply `@functools.lru_cache` to drastically reduce redundant string operations.
