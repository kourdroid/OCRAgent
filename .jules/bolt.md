## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Connection Pooling in High-Frequency Endpoints]
**Learning:** Establishing direct database connections (e.g., using `asyncpg.connect()`) in high-frequency endpoints like `/health` causes significant overhead due to repetitive TCP/TLS handshakes and authentication, which can lead to connection exhaustion and increased latency.
**Action:** Always use a shared database connection pool (e.g., `get_connection_pool`) for endpoints that are called frequently, such as health checks, to reuse connections and reduce overhead.
