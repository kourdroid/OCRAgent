## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-11-20 - [Regex Pre-compilation and LRU Caching]
**Learning:** Functions called frequently in tight loops (like `_normalize_description` and `_sanitize_for_match`) can become bottlenecks due to repeated compilation of identical regular expressions.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Furthermore, when a string normalization function accepts an `Any` type, wrap it with `@functools.lru_cache` but cast the argument to `str` first to avoid `TypeError: unhashable type`.

## 2024-05-18 - [difflib SequenceMatcher Initialization Impact]
 **Learning:** In Python text-processing loops, `difflib.SequenceMatcher` performance can be heavily optimized not just by hoisting initialization and using `quick_ratio()`, but also by assigning the static string to `b` (e.g., `matcher = difflib.SequenceMatcher(None, b=static_string)`) because difflib caches sequence heuristics for sequence `b`.
 **Action:** Update the comparison string in the loop using `matcher.set_seq1(dynamic_string)` when caching against a constant reference to maximize standard library speed.
