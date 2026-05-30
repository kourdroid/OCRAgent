## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Database Connection Pools in Health Checks]
**Learning:** Direct `asyncpg.connect()` calls inside high-frequency endpoints like `/health` cause expensive TCP/TLS handshake and database authentication overhead on each request.
**Action:** Always reuse a shared connection pool (e.g., `get_connection_pool`) for health checks and API endpoints rather than spawning direct database connections.
