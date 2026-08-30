from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from src.ingest.database import get_connection
from src.ingest.entity_resolution import normalize_plate
from src.pipeline.ledger import (
    get_pipeline_state,
    upsert_pipeline_state,
)
from src.pipeline.state import PipelineState
from src.pipeline.utils import (
    AUDIT_DIR,
    OUTPUT_DIR,
    append_jsonl,
    content_hash,
    new_id,
    utc_now,
)
from src.rules_engine.engine import evaluate


REQUIRED_TICKET_FIELDS = {
    "ticket_id",
}


def _audit(
    state: PipelineState,
    node: str,
    decision: str,
    data: dict | None = None,
    rule_ids: list[str] | None = None,
    llm_call_id: str | None = None,
) -> None:

    event = {
        "timestamp": utc_now(),
        "ticket_id": state.get("ticket_id"),
        "node": node,
        "decision": decision,
        "data": data or {},
        "rule_ids": rule_ids or [],
        "llm_call_id": llm_call_id,
    }

    append_jsonl(
        AUDIT_DIR / "audit.jsonl",
        event,
    )


# ============================================================
# VALIDATE
# ============================================================

def validate_node(
    state: PipelineState,
) -> PipelineState:

    ticket = state["ticket"]

    ticket_id = ticket.get(
        "ticket_id"
    )

    state["current_node"] = "validate"

    if not ticket_id:

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            "missing ticket_id"
        )

        _audit(
            state,
            "validate_node",
            "quarantine",
            {
                "reason":
                    state["quarantine_reason"]
            },
        )

        return state

    state["ticket_id"] = str(
        ticket_id
    )

    ticket_hash = content_hash(
        ticket
    )

    state["content_hash"] = (
        ticket_hash
    )

    missing = [
        field
        for field in REQUIRED_TICKET_FIELDS
        if not ticket.get(field)
    ]

    if missing:

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            "missing required fields: "
            + ", ".join(missing)
        )

        upsert_pipeline_state(
            ticket_id=state["ticket_id"],
            content_hash=ticket_hash,
            status="quarantine",
        )

        _audit(
            state,
            "validate_node",
            "quarantine",
            {
                "reason":
                    state["quarantine_reason"]
            },
        )

        return state

    existing = get_pipeline_state(
        state["ticket_id"]
    )

    if existing:

        if existing["content_hash"] == ticket_hash:

            state["status"] = "duplicate"

            state["work_order_id"] = (
                existing["work_order_id"]
            )

            state["notification_id"] = (
                existing["notification_id"]
            )

            _audit(
                state,
                "validate_node",
                "duplicate",
                {
                    "existing_status":
                        existing["status"]
                },
            )

            return state

    state["status"] = "valid"

    upsert_pipeline_state(
        ticket_id=state["ticket_id"],
        content_hash=ticket_hash,
        status="validated",
    )

    _audit(
        state,
        "validate_node",
        "validated",
    )

    return state


# ============================================================
# ENRICH
# ============================================================

def enrich_node(
    state: PipelineState,
) -> PipelineState:

    ticket = state["ticket"]

    state["current_node"] = "enrich"

    vehicle = None
    driver = None
    trip = None
    maintenance = []

    vehicle_raw = (
        ticket.get("vehicle")
        or ticket.get("vehicle_reg")
        or ticket.get("vehicle_registration")
    )

    driver_id = ticket.get(
        "driver_id"
    )

    if vehicle_raw:

        normalized = normalize_plate(
            str(vehicle_raw)
        )

        with get_connection() as db:

            row = db.execute(
                """
                SELECT *
                FROM vehicles
                WHERE normalized_registration = ?
                """,
                (normalized,),
            ).fetchone()

            if row:
                vehicle = dict(row)

            rows = db.execute(
                """
                SELECT *
                FROM maintenance_events
                WHERE normalized_vehicle_reg = ?
                ORDER BY service_date DESC
                LIMIT 20
                """,
                (normalized,),
            ).fetchall()

            maintenance = [
                dict(r)
                for r in rows
            ]

    if driver_id:

        with get_connection() as db:

            row = db.execute(
                """
                SELECT *
                FROM drivers
                WHERE driver_id = ?
                """,
                (str(driver_id),),
            ).fetchone()

            if row:
                driver = dict(row)

    trip_id = ticket.get(
        "trip_id"
    )

    if trip_id:

        with get_connection() as db:

            row = db.execute(
                """
                SELECT *
                FROM trips
                WHERE trip_id = ?
                """,
                (str(trip_id),),
            ).fetchone()

            if row:
                trip = dict(row)

    state["vehicle"] = vehicle
    state["driver"] = driver
    state["trip"] = trip
    state["maintenance"] = maintenance

    if vehicle is None and vehicle_raw:

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            f"vehicle not found: {vehicle_raw}"
        )

    _audit(
        state,
        "enrich_node",
        (
            "enriched"
            if vehicle is not None
            else "vehicle_not_found"
        ),
        {
            "vehicle_found":
                vehicle is not None,
            "driver_found":
                driver is not None,
            "trip_found":
                trip is not None,
            "maintenance_count":
                len(maintenance),
        },
    )

    return state


# ============================================================
# CLASSIFY
# ============================================================

def _get_llm():

    from src.llm.client import get_llm

    return get_llm()


def classify_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = "classify"

    ticket = state["ticket"]

    rules_facts = {
        "vehicle":
            state.get("vehicle"),
        "driver":
            state.get("driver"),
        "maintenance":
            state.get("maintenance", []),
    }

    prompt = f"""
You are the Meridian dispatch classifier.

Classify the operational severity of this ticket.

Return ONLY JSON:

{{
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "category": "BREAKDOWN|DELAY|MAINTENANCE|OTHER",
  "reason": "short explanation"
}}

Use the ticket and structured operational facts.

Do not invent facts.

Ticket:
{json.dumps(ticket, default=str)}

Structured facts:
{json.dumps(rules_facts, default=str)}
"""

    state["classification_prompt"] = prompt

    try:

        llm = _get_llm()

        call_id = new_id("llm")

        response = llm.invoke(
            prompt
        )

        content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )

        state["classification_response"] = (
            content
        )

        state["llm_call_id"] = call_id

        try:
            classification = json.loads(
                content
            )
        except json.JSONDecodeError:

            classification = {
                "severity": "MEDIUM",
                "category": "OTHER",
                "reason": content[:500],
            }

        state["classification"] = (
            classification
        )

        _audit(
            state,
            "classify_node",
            "classified",
            {
                "classification":
                    classification,
            },
            llm_call_id=call_id,
        )

    except Exception as exc:

        # Safe deterministic fallback.
        classification = {
            "severity": "MEDIUM",
            "category": "BREAKDOWN",
            "reason": (
                "LLM classification unavailable; "
                "defaulted to MEDIUM."
            ),
        }

        state["classification"] = (
            classification
        )

        _audit(
            state,
            "classify_node",
            "llm_failed_fallback",
            {
                "error": str(exc),
            },
        )

    return state


# ============================================================
# SELECT VEHICLE
# ============================================================

def select_vehicle_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = (
        "select_vehicle"
    )

    ticket = state["ticket"]

    origin_hub = (
        ticket.get("origin_hub")
        or ticket.get("home_hub")
    )

    destination = (
        ticket.get("destination")
        or ticket.get("destination_name")
        or ""
    )

    client = (
        ticket.get("client")
        or ""
    )

    breakdown_distance = float(
        ticket.get(
            "distance_from_origin_km",
            999999,
        )
    )

    # ---------------------------------------------------------
    # Origin hub override
    # ---------------------------------------------------------

    if breakdown_distance <= 50:

        origin_hub_replacement = (
            state.get("origin_hub")
            or origin_hub
        )

        candidate_hub = (
            origin_hub_replacement
        )

    else:

        candidate_hub = origin_hub

    # ---------------------------------------------------------
    # Candidate vehicles
    # ---------------------------------------------------------

    with get_connection() as db:

        if candidate_hub:

            rows = db.execute(
                """
                SELECT *
                FROM vehicles
                WHERE home_hub = ?
                  AND status = 'Active'
                """,
                (candidate_hub,),
            ).fetchall()

        else:

            rows = db.execute(
                """
                SELECT *
                FROM vehicles
                WHERE status = 'Active'
                """
            ).fetchall()

    candidates = [
        dict(row)
        for row in rows
    ]

    state["candidate_vehicles"] = (
        candidates
    )

    eligible = []
    checked_rules = []

    ticket_date = ticket.get(
        "date"
    )

    if not ticket_date:

        ticket_date = datetime.now().date()

    trip_context = {
        "client": client,
        "destination": destination,
        "destination_region":
            ticket.get(
                "destination_region",
                destination,
            ),
        "origin_hub": origin_hub,
        "breakdown_distance_from_origin_km":
            breakdown_distance,
        "hill_route":
            ticket.get(
                "hill_route",
                False,
            ),
        "night_run":
            ticket.get(
                "night_run",
                False,
            ),
        "solo":
            ticket.get(
                "solo",
                True,
            ),
        "service_due_date":
            ticket.get(
                "service_due_date"
            ),
        "last_brake_work_date":
            ticket.get(
                "last_brake_work_date"
            ),
        "route_east_of_lucknow":
            ticket.get(
                "route_east_of_lucknow",
                False,
            ),
    }

    for candidate in candidates:

        is_eligible, rules = evaluate(
            vehicle=candidate,
            trip_context=trip_context,
            driver=state.get("driver"),
            today=ticket_date,
        )

        checked_rules.extend(
            rules
        )

        if is_eligible:
            eligible.append(
                candidate
            )

    # Deduplicate rule IDs.

    checked_rules = list(
        dict.fromkeys(checked_rules)
    )

    state["eligible_vehicles"] = (
        eligible
    )

    state["checked_rule_ids"] = (
        checked_rules
    )

    if not eligible:

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            "no eligible vehicle available"
        )

        _audit(
            state,
            "select_vehicle_node",
            "quarantine",
            {
                "candidate_count":
                    len(candidates),
                "checked_rule_ids":
                    checked_rules,
            },
            rule_ids=checked_rules,
        )

        return state

    # Prefer the first eligible vehicle.
    selected = eligible[0]

    state["selected_vehicle"] = (
        selected
    )

    _audit(
        state,
        "select_vehicle_node",
        "vehicle_selected",
        {
            "vehicle_id":
                selected.get("vehicle_id"),
            "registration_number":
                selected.get(
                    "registration_number"
                ),
        },
        rule_ids=checked_rules,
    )

    return state


# ============================================================
# WORK ORDER
# ============================================================

def work_order_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = (
        "work_order"
    )

    ticket_id = state["ticket_id"]

    existing = get_pipeline_state(
        ticket_id
    )

    if (
        existing
        and existing["work_order_id"]
    ):

        state["work_order_id"] = (
            existing["work_order_id"]
        )

        _audit(
            state,
            "work_order_node",
            "existing_work_order_reused",
            {
                "work_order_id":
                    existing["work_order_id"]
            },
        )

        return state

    work_order_id = new_id(
        "WO"
    )

    selected = (
        state.get("selected_vehicle")
        or {}
    )

    classification = (
        state.get("classification")
        or {}
    )

    work_order = {
        "work_order_id":
            work_order_id,
        "ticket_id":
            ticket_id,
        "created_at":
            utc_now(),
        "vehicle_id":
            selected.get(
                "vehicle_id"
            ),
        "vehicle_registration":
            selected.get(
                "registration_number"
            ),
        "severity":
            classification.get(
                "severity"
            ),
        "category":
            classification.get(
                "category"
            ),
        "status":
            "OPEN",
        "rule_ids":
            state.get(
                "checked_rule_ids",
                [],
            ),
    }

    append_jsonl(
        OUTPUT_DIR
        / "work_orders.jsonl",
        work_order,
    )

    upsert_pipeline_state(
        ticket_id=ticket_id,
        content_hash=state[
            "content_hash"
        ],
        status="work_order_created",
        work_order_id=work_order_id,
    )

    state["work_order_id"] = (
        work_order_id
    )

    state["work_order"] = (
        work_order
    )

    _audit(
        state,
        "work_order_node",
        "created",
        work_order,
        rule_ids=state.get(
            "checked_rule_ids",
            [],
        ),
    )

    return state


# ============================================================
# DRAFT NOTIFICATION
# ============================================================


def draft_notification_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = (
        "draft_notification"
    )

    ticket_id = state["ticket_id"]

    existing = get_pipeline_state(
        ticket_id
    )

    if (
        existing
        and existing["notification_id"]
    ):

        state["notification_id"] = (
            existing["notification_id"]
        )

        _audit(
            state,
            "draft_notification_node",
            "existing_notification_reused",
            {
                "notification_id":
                    existing[
                        "notification_id"
                    ]
            },
        )

        return state

    ticket = state["ticket"]

    client = (
        ticket.get("client")
        or "the client"
    )

    work_order = (
        state.get("work_order")
        or {}
    )

    prompt = f"""
Draft a concise professional logistics
notification to {client}.

This is a DRAFT only.

Do not claim that the message was sent.

Ticket:
{json.dumps(ticket, default=str)}

Work order:
{json.dumps(work_order, default=str)}

Selected vehicle:
{json.dumps(
    state.get("selected_vehicle"),
    default=str
)}

Classification:
{json.dumps(
    state.get("classification"),
    default=str
)}

Rules checked:
{json.dumps(
    state.get("checked_rule_ids", []),
    default=str
)}

Write only the message body.
"""

    try:

        llm = _get_llm()

        call_id = new_id("llm")

        response = llm.invoke(
            prompt
        )

        message = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )

    except Exception:

        call_id = None

        message = (
            f"Dear {client},\n\n"
            "We have received your operational "
            "request and created a work order. "
            "Our operations team is coordinating "
            "the next steps.\n\n"
            "Regards,\n"
            "Meridian Operations"
        )

    notification_id = new_id(
        "COM"
    )

    notification = {
        "notification_id":
            notification_id,
        "ticket_id":
            state["ticket_id"],
        "work_order_id":
            state.get(
                "work_order_id"
            ),
        "client":
            client,
        "message":
            message,
        "status":
            "PENDING_APPROVAL",
        "citations": [
            {
                "rule_id":
                    rule_id
            }
            for rule_id
            in state.get(
                "checked_rule_ids",
                [],
            )
        ],
        "created_at":
            utc_now(),
    }

    append_jsonl(
        OUTPUT_DIR
        / "comms_pending.jsonl",
        notification,
    )

    upsert_pipeline_state(
        ticket_id=state["ticket_id"],
        content_hash=state[
            "content_hash"
        ],
        status="notification_pending",
        work_order_id=state.get(
            "work_order_id"
        ),
        notification_id=notification_id,
    )

    state["notification_id"] = (
        notification_id
    )

    state["notification"] = (
        notification
    )

    _audit(
        state,
        "draft_notification_node",
        "draft_created",
        {
            "notification_id":
                notification_id
        },
        rule_ids=state.get(
            "checked_rule_ids",
            [],
        ),
        llm_call_id=call_id,
    )

    return state



# ============================================================
# QUARANTINE
# ============================================================

def quarantine_node(
    state: PipelineState,
) -> PipelineState:

    reason = state.get(
        "quarantine_reason",
        "unknown validation failure",
    )

    record = {
        "ticket_id":
            state.get("ticket_id"),
        "reason":
            reason,
        "status":
            "QUARANTINED",
        "created_at":
            utc_now(),
    }

    append_jsonl(
        OUTPUT_DIR
        / "quarantine.jsonl",
        record,
    )

    upsert_pipeline_state(
        ticket_id=state.get(
            "ticket_id",
            "unknown",
        ),
        content_hash=state.get(
            "content_hash",
            "",
        ),
        status="quarantine",
    )

    state["status"] = (
        "quarantine"
    )

    _audit(
        state,
        "quarantine_node",
        "quarantined",
        record,
    )

    return state


# ============================================================
# AUDIT NODE
# ============================================================

def audit_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = "audit"

    # Individual nodes already write detailed audit
    # records. This node records the graph transition.

    _audit(
        state,
        "audit_node",
        "pipeline_transition",
        {
            "status":
                state.get("status"),
        },
        rule_ids=state.get(
            "checked_rule_ids",
            [],
        ),
        llm_call_id=state.get(
            "llm_call_id"
        ),
    )

    return state