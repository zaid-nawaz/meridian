from __future__ import annotations

from src.retrieval.vector_store import VectorStore


def search_documents(
    query: str,
    limit: int = 5,
    corpus: str | None = None,
) -> list[dict]:
    """
    Search the unstructured corpus.

    Optionally restrict results to a corpus:

        email

        dispatcher_interview
    """

    store = VectorStore()

    results = store.search(
        query=query,
        limit=limit,
    )

    if corpus is not None:

        results = [
            result
            for result in results
            if result["metadata"].get(
                "corpus"
            ) == corpus
        ]

    return results


if __name__ == "__main__":

    query = input(
        "Search query: "
    ).strip()

    results = search_documents(
        query,
        limit=5,
    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        print(
            f"\n--- Result {index} ---"
        )

        print(
            "Source:",
            result["metadata"]["source"],
        )

        print(
            "Corpus:",
            result["metadata"]["corpus"],
        )

        print(
            "Distance:",
            result["distance"],
        )

        print(
            "\n",
            result["text"],
        )