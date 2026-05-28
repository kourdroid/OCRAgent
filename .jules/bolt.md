## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2026-05-28 - [Health Check Connection Pooling]
**Learning:** Creating direct database connections (`asyncpg.connect`) on every call to high-frequency endpoints like `/health` introduces significant overhead from TCP/TLS handshakes and database authentication.
**Action:** Always import and reuse the shared connection pool (`get_connection_pool`) using the `async with pool.acquire()` pattern for high-frequency or lightweight API endpoints to mitigate latency and connection exhaustion.
