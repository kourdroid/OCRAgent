## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Caching Any Types]
**Learning:** When using `@functools.lru_cache` to memoize functions that receive `Any` types (like string normalisation helpers), passing unhashable types directly raises a `TypeError`.
**Action:** Cast `Any` inputs to a hashable type (like `str`) inside an outer function before passing the clean input to the memoized core function.
