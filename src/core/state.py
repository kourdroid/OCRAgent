from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    job_id: str
    file_path: str

    detected_vendor: Optional[str]
    fingerprint_hash: Optional[str]

    current_schema: Optional[dict[str, Any]]
    proposed_schema: Optional[dict[str, Any]]

    ocr_text_cache: Optional[str]
    drift_confidence: float

    final_output: Optional[dict[str, Any]]
    error: Optional[str]
