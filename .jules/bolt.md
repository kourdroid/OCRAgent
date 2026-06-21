## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-21 - [Precompute Tokens for O(N*M) Operations]
**Learning:** In nested loops performing string matching across collections (like 3-way matching invoices against POs), running string splitting and normalization inside the inner loop creates an O(N*M) bottleneck.
**Action:** Extract the repeated normalization and tokenization steps into precomputed structures (like a dataclass) before the loop. This reduces string manipulation from O(N*M) to O(N+M), significantly improving performance on large datasets.
