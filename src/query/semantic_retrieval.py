from __future__ import annotations

from src.query.evidence import (
    Citation,
    Evidence,
    EvidencePack,
)
from src.retrieval.search import search_documents


def distance_to_relevance(
    distance: float,
) -> float:
    """
    Convert cosine distance into a simple relevance score.

    Chroma cosine distance:

        0.0 = very similar

    Larger = less similar.
    """

    relevance = 1.0 - distance

    return max(
        0.0,
        min(1.0, relevance),
    )


def retrieve_semantic(
    query: str,
    limit: int = 5,
) -> EvidencePack:

    pack = EvidencePack(
        query=query
    )

    results = search_documents(
        query=query,
        limit=limit,
    )

    for index, result in enumerate(
        results
    ):

        metadata = result["metadata"]

        relevance = distance_to_relevance(
            result["distance"]
        )

        source = metadata["source"]

        chunk_index = metadata[
            "chunk_index"
        ]

        corpus = metadata["corpus"]

        pack.add(
            Evidence(
                evidence_id=(
                    f"semantic-{index}"
                ),
                source_type="semantic",
                content=result["text"],
                relevance=relevance,
                citation=Citation(
                    citation_id=(
                        f"semantic-{index}"
                    ),
                    source_type="text",
                    source=source,
                    location=(
                        f"chunk={chunk_index}"
                    ),
                    description=(
                        f"{corpus} corpus"
                    ),
                ),
            )
        )

    return pack