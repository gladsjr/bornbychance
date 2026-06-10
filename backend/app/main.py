"""
API do Born by Chance.

  GET  /api/places          -> lista de lugares disponiveis
  POST /api/draw            -> sorteia uma vida {place, year_from, year_to, seed?}
  GET  /                    -> interface web
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import draw
from .narrative import build_narrative

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

app = FastAPI(title="Born by Chance", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class DrawRequest(BaseModel):
    place: str = Field(..., examples=["Brazil"])
    year_from: int = Field(..., ge=-12000, le=2023)
    year_to: int = Field(..., ge=-12000, le=2023)
    seed: int | None = None


@app.get("/api/places")
def places() -> dict:
    from .data_loader import get_store

    return {"places": get_store().places()}


@app.post("/api/draw")
def draw_life(req: DrawRequest) -> dict:
    result = draw(req.place, req.year_from, req.year_to, seed=req.seed)
    result["narrative"] = build_narrative(result)
    return result


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# frontend estatico (montado por ultimo para nao engolir as rotas /api)
if FRONTEND_DIR.exists():
    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
