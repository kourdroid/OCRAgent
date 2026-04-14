# Full Audit & Fix Plan: Missing Dependencies and Broken Imports

I have identified the root cause of the `ModuleNotFoundError` and other potential issues.

## 1. `ModuleNotFoundError: No module named 'google.api_core'`
**Cause:** `src/core/nodes.py` still imports `from google.api_core.exceptions import NotFound`. The new `google-genai` SDK does not include `google-api-core` as a direct dependency, or uses a different structure.
**Fix:**
*   Remove `from google.api_core.exceptions import NotFound`.
*   Replace usage with `google.genai.errors.ClientError` or catch generic `Exception` (since the new SDK wraps errors differently).
*   Specifically, `genai.Client` methods raise `google.genai.errors.APIError` or similar. I will update the exception handling to match the new SDK.

## 2. Audit of Other Files
I will proactively check for other legacy imports:
*   `src/core/graph.py`: Check for `google.generativeai` imports.
*   `src/api/routes.py`: Check for `google.generativeai` imports.
*   `src/worker/worker.py`: Check for `google.generativeai` imports.

## 3. Verify `requirements.txt`
*   Ensure `python-multipart` is present (already added).
*   Ensure `google-genai` is the only Google GenAI dependency.

## Execution Steps
1.  **Refactor `src/core/nodes.py`**: Remove `google.api_core` import and fix exception handling.
2.  **Audit other files**: Grep for `google.api_core` and `google.generativeai` in the entire `src/` directory to be 100% sure.
3.  **Rebuild**: Run `docker-compose up --build` to apply changes.

I will now proceed with fixing `src/core/nodes.py` and auditing the rest of the codebase.
