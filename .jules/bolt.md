## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Fuzzy Match Precomputation]
**Learning:** During 3-way matching, O(N*M) nested loops performing repetitive string normalization and tokenization create a noticeable bottleneck as invoice line items scale.
**Action:** Extract the repetitive string operations from the loop, precompute normalized strings and token sets into lists of tuples `list[tuple[dict, str, set]]`, and perform O(N*M) set intersections instead. This provides ~10x speedup while avoiding side-effects.
