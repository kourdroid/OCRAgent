## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Optimize O(N*M) Match Overhead]
**Learning:** Calling repetitive string transformations (regex, lower, splitting) in nested loops is a severe bottleneck, even in pure Python.
**Action:** Precompute these values into tuples or dataclasses outside loops and use fast, inline-able comparisons inside the loop.
