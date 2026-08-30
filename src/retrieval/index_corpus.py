from __future__ import annotations

import json
from pathlib import Path

from src.retrieval.vector_store import VectorStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


CORPUS_FILES = {
    "email": PROCESSED_DIR / "emails.jsonl",
    "dispatcher_interview": (
        PROCESSED_DIR
        / "dispatcher_interview.jsonl"
    ),
}


def load_jsonl(path: Path) -> list[dict]:
    """
    Load JSONL records.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Corpus file not found: {path}"
        )

    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            records.append(
                json.loads(line)
            )

    return records


def build_documents(
    corpus: str,
    records: list[dict],
) -> list[dict]:
    """
    Convert JSONL records into vector-store documents.
    """

    documents = []

    for record in records:

        source = record["source"]

        chunk_index = record["chunk_index"]

        document_id = (
            f"{corpus}:"
            f"{source}:"
            f"{chunk_index}"
        )

        documents.append(
            {
                "id": document_id,
                "text": record["text"],
                "metadata": {
                    "corpus": corpus,
                    "source": source,
                    "chunk_index": chunk_index,
                },
            }
        )

    return documents


def index_corpus() -> int:
    """
    Index all processed text corpora.
    """

    vector_store = VectorStore()

    total = 0

    for corpus, path in CORPUS_FILES.items():

        print(
            f"Loading {corpus}: {path}"
        )

        records = load_jsonl(path)

        documents = build_documents(
            corpus,
            records,
        )

        vector_store.add_documents(
            documents
        )

        print(
            f"Indexed {len(documents)} "
            f"{corpus} chunks."
        )

        total += len(documents)

    return total


if __name__ == "__main__":

    count = index_corpus()

    print(
        f"\nTotal indexed documents: {count}"
    )