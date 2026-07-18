## 2024-05-24 - [SequenceMatcher Optimization in OCR loop]
**Learning:** In Python text-processing loops, `difflib.SequenceMatcher` performance can be heavily optimized by hoisting initialization and assigning the static string to `b` (e.g., `matcher = difflib.SequenceMatcher(None, b=static_string)`) because difflib caches heuristics for sequence `b`.
**Action:** Update the comparison string in the loop using `matcher.set_seq1(dynamic_string)`, and pre-filter with `matcher.quick_ratio()` before invoking the expensive `matcher.ratio()` method.
