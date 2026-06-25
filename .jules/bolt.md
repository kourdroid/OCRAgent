## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Redundant String Operations in N*M Loops]
**Learning:** Performing expensive string normalizations and regex replacements inside a nested O(N*M) matching loop creates a significant performance bottleneck, especially as the number of items grows.
**Action:** Precompute normalized values (and tokens for set operations) outside the main loop and store them in local tuple structures. Pass these precomputed values to matching functions to reduce string op complexity to O(N + M).
