## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Optimize Text Normalization in Loops]
**Learning:** In the `execute_3_way_match` function, `_normalize_description` is called repeatedly for identical description strings across purchase order lines and invoice lines. The repeated regex recompilation and string manipulation create unnecessary overhead.
**Action:** Pre-compile regular expressions at the module level. Use `@functools.lru_cache` to memoize functions performing string normalizations, but remember to cast inputs to string (or another hashable type) to avoid `TypeError: unhashable type`.
