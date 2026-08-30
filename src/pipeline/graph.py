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


# ============================================================
# ROUTING
# ============================================================

def route_from_audit(
    state: PipelineState,
) -> str:
    """
    Decide what happens after the audit node.

    `last_node` tells us which pipeline node ran
    immediately before audit.
    """

    # ---------------------------------------------------------
    # Quarantine always wins.
    # ---------------------------------------------------------

    if state.get("status") == "quarantine":
        return "quarantine"

    last_node = state.get(
        "last_node"
    )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if last_node == "validate":

        if state.get("status") == "duplicate":
            return "end"

        return "enrich"

    # ---------------------------------------------------------
    # Enrichment
    # ---------------------------------------------------------

    if last_node == "enrich":
        return "classify"

    # ---------------------------------------------------------
    # Classification
    # ---------------------------------------------------------

    if last_node == "classify":
        return "select_vehicle"

    # ---------------------------------------------------------
    # Vehicle selection
    # ---------------------------------------------------------

    if last_node == "select_vehicle":
        return "work_order"

    # ---------------------------------------------------------
    # Work order
    # ---------------------------------------------------------

    if last_node == "work_order":
        return "draft_notification"

    # ---------------------------------------------------------
    # Notification
    # ---------------------------------------------------------

    if last_node == "draft_notification":
        return "end"

    # ---------------------------------------------------------
    # Defensive fallback
    # ---------------------------------------------------------

    return "end"


# ============================================================
# GRAPH
# ============================================================

def build_graph():

    graph = StateGraph(
        PipelineState
    )

    # ---------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    graph.add_edge(
        START,
        "validate",
    )

    # ---------------------------------------------------------
    # Every processing node goes through audit.
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Audit decides the next node.
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "audit",
        route_from_audit,
        {
            "enrich":
                "enrich",

            "classify":
                "classify",

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

    # ---------------------------------------------------------
    # Quarantine terminates the ticket.
    # ---------------------------------------------------------

    graph.add_edge(
        "quarantine",
        END,
    )

    return graph.compile()