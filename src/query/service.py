from __future__ import annotations

from src.query.answer import generate_answer
from src.query.models import QueryResponse
from src.query.retrieval_service import retrieve


def ask(
    query: str,
) -> QueryResponse:
    """
    Complete Meridian query pipeline.
    """

    query = query.strip()

    if not query:

        return QueryResponse(
            answer=(
                "Please provide a question."
            ),
            citations=[],
            sufficient_evidence=False,
        )

    evidence = retrieve(query)

    return generate_answer(
        query=query,
        pack=evidence,
    )