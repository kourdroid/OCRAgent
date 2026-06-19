## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2025-02-27 - O(N*M) Normalization Bottleneck in 3-Way Match
**Learning:** In `execute_3_way_match`, calling string normalization (`_normalize_description`) and tokenization (`.split()`) inside a nested loop over invoice items against all PO and receipt lines caused an O(N*M) explosion in string processing overhead. Since PO and Receipt lines are static for the duration of the match, their normalized forms and token arrays should be computed *once*.
**Action:** Precompute computationally expensive derivatives (like lowercase/regex stripped strings and split arrays) for static sets of data before entering the main loop when doing N*M comparisons.
