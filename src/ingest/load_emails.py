from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import TextLoader

from src.ingest.text_corpus import (
    PROCESSED_DIR,
    create_text_splitter,
    write_chunks,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EMAILS_DIR = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "emails"
)

OUTPUT_PATH = (
    PROCESSED_DIR
    / "emails.jsonl"
)


def load_emails() -> int:
    """
    Load all .txt email files, split them into chunks,
    and write the resulting corpus to JSONL.
    """

    if not EMAILS_DIR.exists():
        raise FileNotFoundError(
            f"Emails directory not found: {EMAILS_DIR}"
        )

    email_files = sorted(
        EMAILS_DIR.glob("*.txt")
    )

    if not email_files:
        print(
            "No email files found. "
            f"Expected .txt files in {EMAILS_DIR}"
        )

        write_chunks([], OUTPUT_PATH)

        return 0

    splitter = create_text_splitter()

    chunks: list[dict] = []

    for email_path in email_files:

        loader = TextLoader(
            str(email_path),
            encoding="utf-8",
        )

        documents = loader.load()

        split_documents = splitter.split_documents(
            documents
        )

        for index, document in enumerate(
            split_documents
        ):

            chunks.append(
                {
                    "source": email_path.name,
                    "chunk_index": index,
                    "corpus": "email",
                    "text": document.page_content,
                }
            )

    count = write_chunks(
        chunks,
        OUTPUT_PATH,
    )

    return count


if __name__ == "__main__":
    count = load_emails()

    print(
        f"Loaded {count} email chunks."
    )