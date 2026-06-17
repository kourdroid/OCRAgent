## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.
## 2024-12-05 - [Memoize 3-Way Match String Normalization]
**Learning:** The `execute_3_way_match` function runs an O(N*M) nested loop comparing invoice line descriptions against PO and receipt lines. Repeatedly calling `re.sub` dynamically within this loop for identical strings causes unnecessary computational overhead. Also, applying `@functools.lru_cache` to functions taking `Any` fails with unhashable types if a dict or list is passed.
**Action:** Pre-compile regular expressions used in heavy loops, extract text normalization to a dedicated string-only function, apply `lru_cache`, and cast variables (like `Any`) to hashable types (like `str`) *before* passing them to the cached function.
