"""
FastAPI app.

Single endpoint used by BOTH Team A (phone/Bhashini helpline) and
Team C (mobile app) — see the interface contract in the project doc.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from src.service import process_query
from src.config import SUPPORTED_LANGUAGES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PS-21 Team B — RAG + LLM Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConverseRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(default="en")
    session_id: str = Field(...)
    state: Optional[str] = None
    district: Optional[str] = None


class ConverseResponse(BaseModel):
    response: str
    language: str
    session_id: str
    structured: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/converse", response_model=ConverseResponse)
def converse(req: ConverseRequest):
    """
    Never raise a 500 back to a live phone call — process_query already
    catches its own internal errors and returns a safe fallback response,
    so this handler stays a thin pass-through.
    """
    if req.language not in SUPPORTED_LANGUAGES:
        logger.warning("Unsupported language '%s', defaulting to 'en'", req.language)

    result = process_query(
        text=req.text,
        language=req.language,
        session_id=req.session_id,
        state=req.state,
        district=req.district,
    )
    return result
