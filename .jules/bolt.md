## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-07-25 - Connection Pooling in API Endpoints
**Learning:** Establishing a new PostgreSQL connection (`asyncpg.connect`) on every API request (e.g., health check pings) is a significant performance bottleneck due to TCP/TLS handshake and authentication overhead.
**Action:** Always use a shared connection pool (`get_connection_pool` and `pool.acquire()`) for database operations in API routes to minimize connection latency.
