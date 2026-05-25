## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Connection Pooling in High-Frequency Endpoints]
**Learning:** Creating direct database connections (`asyncpg.connect()`) in high-frequency API endpoints like `/health` introduces expensive TCP/TLS handshake and authentication overhead.
**Action:** Avoid direct connections. Import and reuse `get_connection_pool` from `src.infrastructure.supabase_repos` to drastically reduce latency and resource consumption.
