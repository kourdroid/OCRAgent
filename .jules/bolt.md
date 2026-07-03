## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2025-02-28 - [Supply Chain 3-Way Match Optimization]
**Learning:** In purely deterministic nested loops doing string comparison (like `execute_3_way_match`), performing tokenization and normalisation inside the nested loop creates a massive O(N * M) performance hit.
**Action:** Always extract invariant string normalizations and token creations out of inner loops into precomputed dictionaries or lists to reduce the inner loop comparisons to O(1) set operations. Avoid inlining complex matching operations directly into loop comprehensions or loops for readability.
