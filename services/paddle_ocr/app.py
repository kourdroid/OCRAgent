from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

import fitz
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from paddleocr import PaddleOCR
from pydantic import BaseModel, Field


DETECTION_MODEL = os.getenv("PADDLE_DETECTION_MODEL", "PP-OCRv6_small_det")
RECOGNITION_MODEL = os.getenv("PADDLE_RECOGNITION_MODEL", "PP-OCRv6_small_rec")
MODEL_ID = f"{DETECTION_MODEL}+{RECOGNITION_MODEL}"
DEVICE = os.getenv("PADDLE_OCR_DEVICE", "cpu")
ENGINE = os.getenv("PADDLE_OCR_ENGINE", "onnxruntime")
MIN_CONFIDENCE = float(os.getenv("PADDLE_OCR_MIN_CONFIDENCE", "0.45"))
RENDER_DPI = int(os.getenv("PADDLE_OCR_RENDER_DPI", "180"))
MAX_PDF_MB = int(os.getenv("PADDLE_OCR_MAX_PDF_MB", "50"))


class OCRLineResponse(BaseModel):
    text: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)


class OCRPageResponse(BaseModel):
    page: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    lines: list[OCRLineResponse]


class OCRDocumentResponse(BaseModel):
    pages: list[OCRPageResponse] = Field(min_length=1)


_pipeline: PaddleOCR | None = None
_inference_lock = asyncio.Lock()


def _build_pipeline() -> PaddleOCR:
    return PaddleOCR(
        text_detection_model_name=DETECTION_MODEL,
        text_recognition_model_name=RECOGNITION_MODEL,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        engine=ENGINE,
        device=DEVICE,
    )


def _normalize_box(box: Any, *, width: int, height: int) -> list[float]:
    values = np.asarray(box, dtype=float).reshape(-1).tolist()
    if len(values) != 4:
        raise ValueError("PaddleOCR returned an invalid text box")
    x1, y1, x2, y2 = values
    return [
        min(1.0, max(0.0, x1 / width)),
        min(1.0, max(0.0, y1 / height)),
        min(1.0, max(0.0, x2 / width)),
        min(1.0, max(0.0, y2 / height)),
    ]


def _recognize_pdf(pdf_bytes: bytes) -> OCRDocumentResponse:
    if _pipeline is None:
        raise RuntimeError("PaddleOCR is not initialized")

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    if document.page_count < 1:
        raise ValueError("PDF contains no pages")

    scale = RENDER_DPI / 72.0
    pages: list[OCRPageResponse] = []
    try:
        for page_index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height,
                pixmap.width,
                pixmap.n,
            )
            if pixmap.n > 3:
                image = image[:, :, :3]

            results = list(_pipeline.predict(image))
            if len(results) != 1:
                raise RuntimeError("PaddleOCR returned an unexpected page result count")
            payload = results[0].json.get("res", {})
            texts = payload.get("rec_texts") or []
            scores = payload.get("rec_scores") or []
            boxes = payload.get("rec_boxes") or []
            if not (len(texts) == len(scores) == len(boxes)):
                raise RuntimeError("PaddleOCR result arrays have different lengths")

            lines = [
                OCRLineResponse(
                    text=str(text).strip(),
                    confidence=float(score),
                    bbox=_normalize_box(box, width=pixmap.width, height=pixmap.height),
                )
                for text, score, box in zip(texts, scores, boxes, strict=True)
                if str(text).strip() and float(score) >= MIN_CONFIDENCE
            ]
            pages.append(
                OCRPageResponse(
                    page=page_index + 1,
                    width=pixmap.width,
                    height=pixmap.height,
                    lines=lines,
                )
            )
    finally:
        document.close()

    return OCRDocumentResponse(pages=pages)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _pipeline
    _pipeline = await asyncio.to_thread(_build_pipeline)
    yield
    _pipeline = None


app = FastAPI(title="Ironclad PaddleOCR", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok" if _pipeline is not None else "starting",
        "ready": _pipeline is not None,
        "model_id": MODEL_ID,
        "engine": ENGINE,
        "device": DEVICE,
    }


@app.post("/v1/ocr", response_model=OCRDocumentResponse)
async def recognize(file: UploadFile = File(...)) -> OCRDocumentResponse:
    data = await file.read(MAX_PDF_MB * 1024 * 1024 + 1)
    if len(data) > MAX_PDF_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF exceeds the OCR size limit")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported")

    try:
        async with _inference_lock:
            return await asyncio.to_thread(_recognize_pdf, data)
    except (ValueError, fitz.FileDataError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
