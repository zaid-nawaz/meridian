from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src.query.models import QueryResponse
from src.query.service import ask


app = FastAPI(
    title="Meridian Query API",
    version="0.1.0",
)


class AskRequest(BaseModel):

    question: str


@app.get("/health")
def health() -> dict:

    return {
        "status": "ok"
    }


@app.post(
    "/ask",
    response_model=QueryResponse,
)
def ask_question(
    request: AskRequest,
) -> QueryResponse:

    return ask(
        request.question
    )