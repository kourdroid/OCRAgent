## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Connection Pooling in Health Checks]
**Learning:** High-frequency endpoints like `/health` can become CPU and latency bottlenecks if they establish new database connections (`asyncpg.connect()`) on every request, due to TCP/TLS handshakes and PostgreSQL authentication overhead.
**Action:** Always use the shared connection pool (`get_connection_pool`) for database checks in health endpoints to eliminate this per-request overhead.
