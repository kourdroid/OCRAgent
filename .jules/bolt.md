## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Avoid high-frequency DB Connections]
**Learning:** Establishing direct connections (`asyncpg.connect()`) within high-frequency API endpoints like `/health` causes expensive TCP/TLS handshake latency and wastes connection limits.
**Action:** Utilize shared connection pooling (e.g. `get_connection_pool`) and borrow connections via `pool.acquire()` to prevent performance bottlenecks.
