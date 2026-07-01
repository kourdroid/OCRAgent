## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Redundant String Tokenization in Loop]
**Learning:** In the `execute_3_way_match` algorithm, normalizing descriptions and computing tokens for PO and receipt candidates inside an O(N*M) loop caused significant performance bottlenecks.
**Action:** Precompute these normalized strings and token sets outside the loop, reducing the inner loop operation to simple set intersections, turning O(N*M*tokens) into ~O(M) for a 6x speedup.
