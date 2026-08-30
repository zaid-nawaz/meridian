from __future__ import annotations

from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    citation_id: str

    source_type: str

    source: str

    location: str

    description: str


class QueryResponse(BaseModel):
    answer: str

    citations: list[CitationResponse] = Field(
        default_factory=list
    )

    sufficient_evidence: bool