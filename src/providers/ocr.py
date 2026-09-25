from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class OCRLine(BaseModel):
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_bbox(self) -> "OCRLine":
        if any(value < 0.0 or value > 1.0 for value in self.bbox):
            raise ValueError("bbox coordinates must be normalized between 0 and 1")
        if self.bbox[2] < self.bbox[0] or self.bbox[3] < self.bbox[1]:
            raise ValueError("bbox coordinates must form a valid rectangle")
        return self


class OCRPage(BaseModel):
    page: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    lines: list[OCRLine] = Field(default_factory=list)


class OCRDocument(BaseModel):
    pages: list[OCRPage] = Field(min_length=1)


class OCRProvider(Protocol):
    provider_id: str
    model_id: str

    async def healthcheck(self) -> dict[str, str | bool]: ...

    async def recognize_pdf(self, pdf_bytes: bytes) -> OCRDocument: ...
