from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Citation:
    """
    A citation pointing back to the source of evidence.
    """

    citation_id: str

    source_type: str

    source: str

    location: str

    description: str


@dataclass
class Evidence:
    """
    A single piece of retrieved evidence.
    """

    evidence_id: str

    source_type: str

    content: Any

    relevance: float

    citation: Citation


@dataclass
class EvidencePack:
    """
    All evidence retrieved for a user question.
    """

    query: str

    evidence: list[Evidence] = field(
        default_factory=list
    )

    def add(
        self,
        evidence: Evidence,
    ) -> None:
        self.evidence.append(evidence)

    def is_empty(self) -> bool:
        return len(self.evidence) == 0

    def relevant(
        self,
        threshold: float,
    ) -> list[Evidence]:

        return [
            item
            for item in self.evidence
            if item.relevance >= threshold
        ]

    def citations(self) -> list[dict]:
        """
        Return citations in API-friendly format.
        """

        return [
            {
                "citation_id": item.citation.citation_id,
                "source_type": item.citation.source_type,
                "source": item.citation.source,
                "location": item.citation.location,
                "description": item.citation.description,
            }
            for item in self.evidence
        ]