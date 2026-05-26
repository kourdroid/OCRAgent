## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2026-05-26 - [Connection Pool Reuse]
**Learning:** Avoid creating direct database connections (`asyncpg.connect()`) in high-frequency API endpoints like `/health`. Creating new connections incurs an expensive TCP/TLS handshake and authentication overhead, leading to latency spikes and potential connection exhaustion.
**Action:** Import and reuse `get_connection_pool` to leverage the existing shared connection pool, dramatically reducing endpoint latency and overhead.
