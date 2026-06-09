## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2025-03-09 - [Direct DB connections in endpoints]
**Learning:** Establishing direct database connections inside frequent API endpoints (like `/health`) causes performance bottlenecks due to TCP/TLS handshakes and wastes database connection slots.
**Action:** Always verify if a connection pool util (e.g., `get_connection_pool`) is available to reuse connections instead of creating new ones per request.
