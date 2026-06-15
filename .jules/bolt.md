## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-06-15 - [Memoize string normalization]
**Learning:** Functions repeatedly processing identical strings, like description normalization during line-item comparison, benefit significantly from memoization (`lru_cache`). However, when wrapping functions that may receive unhashable inputs (like `Any`), you must wrap the core logic in a helper that receives and caches primitive strings to avoid `TypeError`.
**Action:** Extract the pure string operations into an `@functools.lru_cache` decorated helper, and use the outer function to handle type coercion (`str(value)`). Also, pre-compile regular expressions module-wide to avoid repetitive re-compilation in hot paths.
