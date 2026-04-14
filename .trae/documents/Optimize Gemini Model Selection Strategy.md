I will optimize the Gemini model selection strategy to address the `429 RESOURCE_EXHAUSTED` errors and improve reliability.

### 1. Update Default Configuration (`src/config.py`)

* Change the default `model_name` from `gemini-3-flash-preview` (experimental/unstable) to `gemini-2.5-flash`.

* **Reasoning:** `gemini-2.5-flash` is the current production standard with the most stable quotas and availability. `gemini-3` is a preview model and should only be used if explicitly requested.

### 2. Refactor Model Fallback Logic (`src/core/nodes.py`)

* Rewrite `_model_name_candidates` to implement a robust "Waterfall" strategy:

  1. **Primary:** The configured model (e.g., `gemini-2.5-flash`).
  2. **Fallback 1:** `gemini-2.0-flash` (High performance, next generation).
  3. **Fallback 2:** `gemini-1.5-pro` (Higher capacity/quality backup).

* **Remove:** The hardcoded `gemini-3-flash-preview` variants from the automatic fallback list to prevent wasting quota on experimental models.

* **Improve:** Ensure we don't retry the same model multiple times under different aliases if they share the same quota.

### 3. Verification

* I will run the `curl /health` check to ensure the API is responsive.

* I will manually trigger a test ingestion to verify the new model selection works without 429 errors (assuming the 2`.5-flash` quota is available).

This directly answers your question: "Why check 3 then 2?" -> The code was hardcoded to prioritize experimental v3 models. We are changing it to prioritize stable v1.5/v2 models.
