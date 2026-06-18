## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-20 - [Redundant String Allocations in O(N*M) Match]
**Learning:** In `src/plugins/supply_chain.py`, string normalization using `re.sub` within nested loops (`_find_best_match` comparing `invoice_items` against `po_lines` and `receipt_lines`) causes redundant string allocations and regex evaluations for the same text.
**Action:** Precompile the regex pattern (`_NORMALIZE_RE`) and extract the normalization logic to a helper function decorated with `@functools.lru_cache()`. Ensure `Any` typed inputs are safely coerced to a hashable `str` type before caching to prevent `TypeError: unhashable type`.
