## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-05-18 - [Optimizing the /health endpoint with connection pooling]
**Learning:** High-frequency API endpoints like `/health`, when backed by PostgreSQL databases, suffer severely from TCP/TLS handshake latency if new connections are spawned directly (e.g., via `asyncpg.connect()`).
**Action:** Use a shared connection pool (`get_connection_pool` from `src.infrastructure.supabase_repos`) for all database operations on standard HTTP endpoints to prevent unnecessary overhead and potential connection limits.
