from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import TextLoader

from src.ingest.text_corpus import (
    PROCESSED_DIR,
    create_text_splitter,
    write_chunks,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTERVIEW_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "dispatcher_interview.txt"
)

OUTPUT_PATH = (
    PROCESSED_DIR
    / "dispatcher_interview.jsonl"
)


def load_dispatcher_interview() -> int:
    """
    Load and chunk the dispatcher interview.

    This corpus is intentionally kept separate from emails
    because Phase 4 uses it for rule extraction.
    """

    if not INTERVIEW_PATH.exists():
        raise FileNotFoundError(
            "Dispatcher interview not found: "
            f"{INTERVIEW_PATH}"
        )

    loader = TextLoader(
        str(INTERVIEW_PATH),
        encoding="utf-8",
    )

    documents = loader.load()

    splitter = create_text_splitter()

    split_documents = splitter.split_documents(
        documents
    )

    chunks: list[dict] = []

    for index, document in enumerate(
        split_documents
    ):

        chunks.append(
            {
                "source": INTERVIEW_PATH.name,
                "chunk_index": index,
                "corpus": "dispatcher_interview",
                "text": document.page_content,
            }
        )

    return write_chunks(
        chunks,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    count = load_dispatcher_interview()

    print(
        f"Loaded {count} dispatcher interview chunks."
    )