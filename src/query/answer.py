
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv
from src.query.evidence import EvidencePack
from src.query.models import (
    CitationResponse,
    QueryResponse,
)

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

INSUFFICIENT_DATA_MESSAGE = (
    "I don't have sufficient data to answer "
    "that confidently."
)


def _serialize_evidence(
    pack: EvidencePack,
) -> str:
    relevant = pack.relevant(
        threshold=0.35
    )

    serialized = []

    for item in relevant:
        serialized.append(
            {
                "evidence_id": item.evidence_id,
                "source_type": item.source_type,
                "relevance": item.relevance,
                "content": item.content,
                "citation": {
                    "citation_id": (
                        item.citation.citation_id
                    ),
                    "source": (
                        item.citation.source
                    ),
                    "location": (
                        item.citation.location
                    ),
                    "description": (
                        item.citation.description
                    ),
                },
            }
        )

    return json.dumps(
        serialized,
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _get_llm() -> ChatOpenAI:
    """Construct the OpenRouter-backed LLM."""

    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    )


def generate_answer(
    query: str,
    pack: EvidencePack,
) -> QueryResponse:
    relevant = pack.relevant(
        threshold=0.35
    )

    if not relevant:
        return QueryResponse(
            answer=INSUFFICIENT_DATA_MESSAGE,
            citations=[],
            sufficient_evidence=False,
        )

    llm = _get_llm()

    citations = [
        CitationResponse(
            citation_id=item.citation.citation_id,
            source_type=item.citation.source_type,
            source=item.citation.source,
            location=item.citation.location,
            description=item.citation.description,
        )
        for item in relevant
    ]

    evidence_text = _serialize_evidence(pack)

    prompt = f"""
You are the Meridian operations assistant.

Answer the user's question using ONLY the evidence
provided below.

Do not use outside knowledge.

If the evidence does not support a conclusion,
say that the available data is insufficient.

User question:

{query}

Evidence:

{evidence_text}

Return a concise factual answer.

Do not invent facts, dates, vehicle information,
client policies, or operational rules.
"""

    response = llm.invoke(prompt)

    answer = (
        response.content
        if hasattr(response, "content")
        else str(response)
    )

    return QueryResponse(
        answer=answer,
        citations=citations,
        sufficient_evidence=True,
    )

