from __future__ import annotations

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VECTOR_DB_PATH = PROJECT_ROOT / "db" / "chroma"

COLLECTION_NAME = "meridian_documents"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class VectorStore:
    """
    Local vector store for Meridian's unstructured corpora.
    """

    def __init__(self) -> None:

        VECTOR_DB_PATH.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH)
        )

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine"
            },
        )

    def add_documents(
        self,
        documents: list[dict],
    ) -> None:
        """
        Add documents to the vector database.

        Each document must contain:

        id
        text
        metadata
        """

        if not documents:
            return

        texts = [
            document["text"]
            for document in documents
        ]

        ids = [
            document["id"]
            for document in documents
        ]

        metadatas = [
            document["metadata"]
            for document in documents
        ]

        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
        ).tolist()

        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Perform semantic similarity search.
        """

        query_embedding = self.embedding_model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        documents = result.get(
            "documents",
            [[]],
        )[0]

        metadatas = result.get(
            "metadatas",
            [[]],
        )[0]

        distances = result.get(
            "distances",
            [[]],
        )[0]

        results: list[dict] = []

        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            results.append(
                {
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return results