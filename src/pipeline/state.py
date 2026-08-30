from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # ---------------------------------------------------------
    # Input
    # ---------------------------------------------------------

    ticket: dict[str, Any]

    ticket_id: str
    content_hash: str

    # ---------------------------------------------------------
    # Pipeline control
    # ---------------------------------------------------------

    status: str
    quarantine_reason: str

    current_node: str

    # ---------------------------------------------------------
    # Enrichment
    # ---------------------------------------------------------

    vehicle: dict[str, Any] | None
    driver: dict[str, Any] | None
    trip: dict[str, Any] | None
    maintenance: list[dict[str, Any]]

    # ---------------------------------------------------------
    # Classification
    # ---------------------------------------------------------

    classification: dict[str, Any] | None
    classification_prompt: str | None
    classification_response: str | None
    llm_call_id: str | None

    # ---------------------------------------------------------
    # Vehicle selection
    # ---------------------------------------------------------

    candidate_vehicles: list[dict[str, Any]]
    eligible_vehicles: list[dict[str, Any]]
    selected_vehicle: dict[str, Any] | None
    checked_rule_ids: list[str]

    # ---------------------------------------------------------
    # Work order
    # ---------------------------------------------------------

    work_order_id: str | None
    work_order: dict[str, Any] | None

    # ---------------------------------------------------------
    # Notification
    # ---------------------------------------------------------

    notification_id: str | None
    notification: dict[str, Any] | None

    # ---------------------------------------------------------
    # Audit
    # ---------------------------------------------------------

    audit_events: list[dict[str, Any]]