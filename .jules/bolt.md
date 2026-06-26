## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Precompute string operations before nested loops]
**Learning:** Redundant string normalizations and tokenizations inside nested loops for list matching (like item description comparisons) cause massive O(N*M) processing bottlenecks.
**Action:** Always precompute normalized string formats and split tokens outside the main loop, replacing O(N*M) heavy string parsing with O(N*M) lightweight set overlap checks.
