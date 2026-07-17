## 2025-02-17 - SequenceMatcher Optimization
**Learning:** In Python text-processing loops, `difflib.SequenceMatcher` performance can be heavily optimized by hoisting initialization and assigning the static string to `b` (e.g., `matcher = difflib.SequenceMatcher(None, b=static_string)`) because difflib caches heuristics for sequence `b`.
**Action:** When implementing string matching in tight loops, pre-initialize SequenceMatcher outside the loop, update the comparison string using `matcher.set_seq1()`, and pre-filter with `matcher.quick_ratio()` before calculating the full `ratio()`.
