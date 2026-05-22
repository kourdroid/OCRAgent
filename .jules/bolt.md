## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Supply Chain String Normalization]\n**Learning:** In string normalization involving expensive regexes, repeatedly normalizing the same strings inside O(N*M) nested loops causes huge performance hits in CPU time.\n**Action:** Use a wrapped pure string function with  to memoize the string operations globally per worker. This provides maximum speed up without changing the data structure logic.
## 2024-11-20 - [Supply Chain String Normalization]
**Learning:** In string normalization involving expensive regexes, repeatedly normalizing the same strings inside O(N*M) nested loops causes huge performance hits in CPU time.
**Action:** Use a wrapped pure string function with `@functools.lru_cache` to memoize the string operations globally per worker. This provides maximum speed up without changing the data structure logic.
