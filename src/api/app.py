from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dossier_routes import router as dossier_router
from src.api.admin_routes import router as admin_router
from src.api.routes import router

app = FastAPI(title="Ironclad-OCR")

# Allow the Next.js frontend (host) to reach the API (Docker container).
# In production, restrict allow_origins to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(dossier_router)
app.include_router(admin_router)
