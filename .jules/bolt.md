## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-05-19 - SequenceMatcher Object Initialization Optimization

**Learning:** `difflib.SequenceMatcher` computes and caches heuristics for the `b` sequence upon initialization. Re-instantiating `SequenceMatcher` in a tight loop is highly inefficient if one sequence is static. Using `set_seq1()` or `set_seq2()` allows you to reuse the cached computations. Furthermore, `quick_ratio()` can be used to pre-filter before calling `ratio()`, avoiding computationally expensive operations if the upper bound of the match is already lower than the current best match.

**Action:** Whenever using `difflib.SequenceMatcher` inside a loop, hoist the initialization outside the loop, assign the static string to the `b` parameter, update the dynamic string using `set_seq1()`, and use `quick_ratio()` for fast-pass filtering.
