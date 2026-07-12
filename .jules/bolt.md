## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.
## 2024-11-20 - [SequenceMatcher Optimization]
**Learning:** `difflib.SequenceMatcher` initialization and the `.ratio()` calculation can be a significant bottleneck in tight text-processing loops.
**Action:** Hoist the initialization out of the loop using `matcher = difflib.SequenceMatcher(None, a=static_string)`. Update the comparison string inside the loop using `matcher.set_seq2(dynamic_string)`. Most importantly, use `matcher.quick_ratio()` as a fast filter before invoking the expensive `matcher.ratio()` method.
