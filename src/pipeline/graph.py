from __future__ import annotations

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from src.pipeline.nodes import (
    audit_node,
    classify_node,
    draft_notification_node,
    enrich_node,
    quarantine_node,
    select_vehicle_node,
    validate_node,
    work_order_node,
)
from src.pipeline.state import PipelineState


def route_after_validate(
    state: PipelineState,
) -> str:

    if state.get("status") == "quarantine":
        return "quarantine"

    if state.get("status") == "duplicate":
        return "end"

    return "enrich"


def route_after_enrich(
    state: PipelineState,
) -> str:

    if state.get("status") == "quarantine":
        return "quarantine"

    return "classify"


def route_after_selection(
    state: PipelineState,
) -> str:

    if state.get("status") == "quarantine":
        return "quarantine"

    return "work_order"


def build_graph():

    graph = StateGraph(
        PipelineState
    )

    graph.add_node(
        "validate",
        validate_node,
    )

    graph.add_node(
        "enrich",
        enrich_node,
    )

    graph.add_node(
        "classify",
        classify_node,
    )

    graph.add_node(
        "select_vehicle",
        select_vehicle_node,
    )

    graph.add_node(
        "work_order",
        work_order_node,
    )

    graph.add_node(
        "draft_notification",
        draft_notification_node,
    )

    graph.add_node(
        "quarantine",
        quarantine_node,
    )

    graph.add_node(
        "audit",
        audit_node,
    )

    graph.add_edge(
        START,
        "validate",
    )

    # Every normal node → audit.

    graph.add_edge(
        "validate",
        "audit",
    )

    graph.add_edge(
        "enrich",
        "audit",
    )

    graph.add_edge(
        "classify",
        "audit",
    )

    graph.add_edge(
        "select_vehicle",
        "audit",
    )

    graph.add_edge(
        "work_order",
        "audit",
    )

    graph.add_edge(
        "draft_notification",
        "audit",
    )

    # Routing from audit.

    def route_from_audit(
        state: PipelineState,
    ) -> str:

        node = state.get(
            "current_node"
        )

        status = state.get(
            "status"
        )

        if status == "quarantine":
            return "quarantine"

        if node == "validate":

            if status == "duplicate":
                return "end"

            return "enrich"

        if node == "enrich":
            return "classify"

        if node == "classify":
            return "select_vehicle"

        if node == "select_vehicle":
            return "work_order"

        if node == "work_order":
            return "draft_notification"

        if node == "draft_notification":
            return "end"

        return "end"

    graph.add_conditional_edges(
        "audit",
        route_from_audit,
        {
            "enrich": "enrich",
            "classify": "classify",
            "select_vehicle":
                "select_vehicle",
            "work_order":
                "work_order",
            "draft_notification":
                "draft_notification",
            "quarantine":
                "quarantine",
            "end":
                END,
        },
    )

    graph.add_edge(
        "quarantine",
        END,
    )

    return graph.compile()