from __future__ import annotations

from src.query.evidence import EvidencePack
from src.query.router import route_query
from src.query.semantic_retrieval import (
    retrieve_semantic,
)
from src.query.structured_retrieval import (
    retrieve_structured,
)


DEFAULT_RELEVANCE_THRESHOLD = 0.35


def retrieve(
    query: str,
) -> EvidencePack:
    """
    Retrieve all relevant evidence for a query.
    """

    route = route_query(query)

    structured = retrieve_structured(
        query=query,
        route=route,
    )

    semantic = EvidencePack(
        query=query
    )

    # Semantic search is especially useful for general
    # questions and policy/interview/email questions.
    #
    # We also perform semantic retrieval alongside structured
    # retrieval because a question may require both.
    if route.route in {
        "semantic",
        "vehicle",
        "vehicle_trips",
        "vehicle_maintenance",
        "driver",
    }:

        semantic = retrieve_semantic(
            query=query,
            limit=5,
        )

    combined = EvidencePack(
        query=query
    )

    for item in structured.evidence:
        combined.add(item)

    for item in semantic.evidence:
        combined.add(item)

    return combined


def has_sufficient_evidence(
    pack: EvidencePack,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
) -> bool:

    relevant = pack.relevant(
        threshold
    )

    return len(relevant) > 0