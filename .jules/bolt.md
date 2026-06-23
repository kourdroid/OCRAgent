## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [O(N*M) Redundant String Parsing in 3-Way Match]
**Learning:** In `execute_3_way_match`, calling string normalization and token splitting inside nested loops comparing N invoice items against M purchase order/receipt lines creates an O(N*M) bottleneck, significantly slowing down processing for large documents.
**Action:** Precompute and cache the normalized descriptions and token sets for the candidate lines (POs/Receipts) outside the main loop. Then, compute the invoice item's tokens once and pass them directly to the matching function to reduce operations from O(N*M) string parses to O(N) + O(M) string parses and O(N*M) set comparisons, giving a ~5x speedup.
