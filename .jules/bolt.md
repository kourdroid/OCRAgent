## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-05-24 - [Avoid TLS handshake bottleneck with connection pooling in Storage Layer]
**Learning:** Instantiating `httpx.AsyncClient` inside tight loops for multiple parallel uploads creates immense overhead due to repeated TCP connection initialization and TLS handshakes. Even with `asyncio.gather`, a new client per file drastically limits throughput.
**Action:** Always implement Storage clients as an async context manager and inject a shared HTTP client during its lifecycle. In `SupabaseStorage`, implementing `__aenter__`/`__aexit__` allows sharing a single connection pool across all queued tasks inside a batch, turning O(N) connection overhead into O(1). Remember to also add these dunder methods to test mocks.
