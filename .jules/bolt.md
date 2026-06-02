## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Connection Pooling in High-Frequency Endpoints]
**Learning:** Making direct database connections (`asyncpg.connect()`) in high-frequency APIs like `/health` introduces expensive TCP/TLS handshake overhead that degrades overall application performance.
**Action:** Always import and reuse `get_connection_pool` from `src.infrastructure.supabase_repos` to acquire shared connections for stateless, high-frequency endpoint checks.
