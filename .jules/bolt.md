## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2026-06-14 - [Database Connection Pooling in High-Frequency Endpoints]
**Learning:** The `/health` endpoint was making a direct, unpooled database connection via `asyncpg.connect()`, which presents a significant performance bottleneck due to expensive TCP/TLS handshakes and authentication overhead on every load balancer ping.
**Action:** Always use a shared connection pool (e.g., `get_connection_pool`) for database interactions in frequently accessed API routes to minimize connection latency and reduce database server load.
