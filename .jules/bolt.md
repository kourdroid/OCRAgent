## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2023-10-27 - O(N) Precomputation in 3-Way Match
**Learning:** In `execute_3_way_match`, calling `_normalize_description` and tokenization inside the nested loop resulted in O(N*M) string operations. The repeated string operations and regex matching took a significant amount of time when lists were large.
**Action:** When performing nested loops or repetitive fuzzy matching, pre-calculate normalized strings, sets, or tokens outside the loop. This reduces the time complexity from O(N*M) string/regex operations to O(N + M).
