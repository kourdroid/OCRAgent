## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-05-27 - [Health Check Connection Pool]
**Learning:** Establishing a brand new asyncpg database connection (with TLS handshake and authentication) for every single request on high-frequency API endpoints like `/health` creates unnecessary overhead and latency.
**Action:** Always import and reuse `get_connection_pool` from `src.infrastructure.supabase_repos` instead of creating direct database connections (`asyncpg.connect()`).
