## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-05-29 - [Cache String Normalization in Loops]
**Learning:** In string-heavy parsing or fuzzy matching loops (like comparing `N` invoice line items to `M` PO lines), recalculating regular expressions and string normalizations for identical inputs dominates CPU time. Memoizing `re.sub` string operations using `@functools.lru_cache` on a pure-string helper bypasses unhashable type errors (`TypeError: unhashable type` for `dict`/`list` args) and significantly boosts performance.
**Action:** When applying LRU caches to functions taking generic `Any` arguments, coerce inputs into hashable types (like strings) and offload the actual operation to a memoized sub-function.
