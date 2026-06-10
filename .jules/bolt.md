## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Database Query Performance for the /jobs Endpoint]
**Learning:** The `/jobs` API endpoint queries the `processing_jobs` table using filters by `status` and orders by `created_at DESC`. Without a composite index `(status, created_at DESC)`, PostgreSQL performs a sequential scan and full table sort, taking O(N log N) time which bottlenecks as the application processes more jobs.
**Action:** Adding composite and simple indices on the fields used in the `ORDER BY` clause turns these sorts into an efficient backward B-Tree index scan in O(LIMIT) time.
