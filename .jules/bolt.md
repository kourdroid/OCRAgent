## 2024-11-20 - [Concurrent PDF Uploads]
**Learning:** In backend endpoints processing multiple splits sequentially (like PDF uploads to Supabase), `await` inside a loop creates an N+1 latency bottleneck.
**Action:** Extract the I/O-bound tasks into a list and use `await asyncio.gather(*tasks)` to run them concurrently, dramatically reducing overall request time.

## 2024-11-21 - [Optimize String Matches in execute_3_way_match]
**Learning:** O(N*M) redundant string operations (lowercasing, regex stripping, splitting, building sets) in loops for matching item descriptions bottlenecked the main invoice processing logic. Precomputing token sets inside a tuple rather than modifying object graphs ensures efficiency and thread-safety.
**Action:** Extract text normalization and token creation outside the `M` loop in nested `N x M` processing and precompute them in a `list[tuple[dict, str, set]]` instead of parsing them repeatedly for every element `N`.
