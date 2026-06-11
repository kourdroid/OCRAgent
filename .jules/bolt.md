## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2026-06-11 - [Cache Unhashable Inputs]
**Learning:** When memoizing functions that accept `Any` types (like `_normalize_description`), passing unhashable inputs directly to `@functools.lru_cache` will cause a `TypeError: unhashable type`.
**Action:** Ensure inputs are cast to hashable types (e.g., `str`) before passing them to the cached function to avoid runtime crashes and correctly benefit from memoization.
