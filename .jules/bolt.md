## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2025-02-28 - [Connection Pooling in High Frequency Endpoints]
**Learning:** Avoid creating direct database connections (`asyncpg.connect()`) in high-frequency API endpoints like `/health`. It causes significant TCP/TLS handshake and authentication overhead per request.
**Action:** Always use the shared connection pool `get_connection_pool()` provided in `src.infrastructure.supabase_repos` to reuse connections and reduce latency/database load.
