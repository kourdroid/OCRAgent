## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Connection Pooling in FastAPI Routes]
**Learning:** Initializing connection pools inside a high-frequency route handler (`asyncpg.connect()` or `get_connection_pool()` inside the route) is an architectural anti-pattern that creates clusters of connections per request, rather than reusing them. Connection pools should be managed at the application lifecycle level. However, a module level lazy-initialization pool like `get_connection_pool` can be safely used if it correctly caches the pool across requests.
**Action:** Use application-level connection pool caching strategies. Here, `get_connection_pool` maintains a module-level dictionary `_shared_pools` making it safe to use in routes, preventing expensive TCP/TLS overhead per request.
