## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-06-22 - [Optimized 3-Way Match Redundant String Operations]
**Learning:** In the `execute_3_way_match` function, the initial implementation recalculated string normalization (`_normalize_description`) and token sets (using `set(norm.split())`) for every PO and goods receipt line inside the loop over `invoice_items`. This created an O(N*M) bottleneck for large invoices.
**Action:** Pre-compute the normalized description strings and token sets for PO and receipt lines outside the main loop. Update `_match_score` and `_find_best_match` to accept these pre-computed token sets, reducing string matching to a simple set intersection. This eliminates redundant regex processing and significantly speeds up matching.
