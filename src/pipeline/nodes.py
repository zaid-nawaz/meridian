from __future__ import annotations

import json
from datetime import date, datetime
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
    read_jsonl,
    utc_now,
)

from src.rules_engine.engine import evaluate


# ============================================================
# CONFIG
# ============================================================

REQUIRED_TICKET_FIELDS = {
    "ticket_id",
}


# ============================================================
# GENERAL HELPERS
# ============================================================

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


def _safe_date(value: Any) -> date | None:
    """
    Convert common date representations into date objects.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text:
        return None

    formats = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def _ticket_vehicle_reg(
    ticket: dict,
) -> str | None:

    value = (
        ticket.get("vehicle")
        or ticket.get("vehicle_reg")
        or ticket.get("vehicle_registration")
        or ticket.get("registration_number")
    )

    if value is None:
        return None

    return str(value).strip()


def _ticket_client(
    ticket: dict,
) -> str:

    return str(
        ticket.get("client")
        or ""
    ).strip()


def _append_unique_jsonl(
    path,
    record: dict,
    unique_key: str,
) -> bool:
    """
    Append a record only if its unique key does not
    already exist in the JSONL file.

    Returns True if appended.
    """

    existing = read_jsonl(path)

    value = record.get(unique_key)

    for item in existing:
        if item.get(unique_key) == value:
            return False

    append_jsonl(
        path,
        record,
    )

    return True


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

    # ---------------------------------------------------------
    # Missing ticket ID
    # ---------------------------------------------------------

    if not ticket_id:

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            "missing ticket_id"
        )

        state["content_hash"] = content_hash(
            ticket
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

    # ---------------------------------------------------------
    # Establish ticket identity
    # ---------------------------------------------------------

    state["ticket_id"] = str(
        ticket_id
    )

    ticket_hash = content_hash(
        ticket
    )

    state["content_hash"] = (
        ticket_hash
    )

    # ---------------------------------------------------------
    # Required fields
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Idempotency / duplicate detection
    #
    # Same ticket_id is treated as the same logical ticket.
    # The first occurrence is canonical.
    # ---------------------------------------------------------

    existing = get_pipeline_state(
        state["ticket_id"]
    )

    if existing:

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
                    existing["status"],

                "existing_work_order_id":
                    existing["work_order_id"],

                "existing_notification_id":
                    existing["notification_id"],
            },
        )

        return state

    # ---------------------------------------------------------
    # New valid ticket
    # ---------------------------------------------------------

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

    vehicle_raw = _ticket_vehicle_reg(
        ticket
    )

    driver_id = ticket.get(
        "driver_id"
    )

    trip_id = ticket.get(
        "trip_id"
    )

    # ---------------------------------------------------------
    # Vehicle + maintenance
    # ---------------------------------------------------------

    if vehicle_raw:

        normalized = normalize_plate(
            vehicle_raw
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
                dict(row)
                for row in rows
            ]

    # ---------------------------------------------------------
    # Driver
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Trip
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Store enrichment
    # ---------------------------------------------------------

    state["vehicle"] = vehicle
    state["driver"] = driver
    state["trip"] = trip
    state["maintenance"] = maintenance

    # ---------------------------------------------------------
    # Explicit vehicle supplied but unresolved
    # ---------------------------------------------------------

    if (
        vehicle is None
        and vehicle_raw
    ):

        state["status"] = "quarantine"

        state["quarantine_reason"] = (
            f"vehicle not found: {vehicle_raw}"
        )

        _audit(
            state,
            "enrich_node",
            "vehicle_not_found",
            {
                "vehicle":
                    vehicle_raw
            },
        )

        return state

    _audit(
        state,
        "enrich_node",
        "enriched",
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
# CLASSIFICATION
# ============================================================

def _get_llm():

    from src.llm.client import get_llm

    return get_llm()


def classify_node(
    state: PipelineState,
) -> PipelineState:

    state["current_node"] = "classify"

    ticket = state["ticket"]

    facts = {
        "vehicle":
            state.get("vehicle"),

        "driver":
            state.get("driver"),

        "trip":
            state.get("trip"),

        "maintenance":
            state.get(
                "maintenance",
                [],
            ),
    }

    ticket_severity = (
        ticket.get("severity")
    )

    prompt = f"""
You are the Meridian dispatch classifier.

Classify this operational ticket.

Return ONLY valid JSON:

{{
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "category": "BREAKDOWN|DELAY|MAINTENANCE|OTHER",
  "reason": "short factual explanation"
}}

Rules:

1. Use only the ticket and structured facts.
2. Do not invent facts.
3. Do not make operational decisions that belong
   to the deterministic rules engine.
4. Keep the reason concise.
5. If the ticket already contains a severity,
   preserve that severity exactly.

Ticket-provided severity:

{ticket_severity}

Ticket:

{json.dumps(
    ticket,
    ensure_ascii=False,
    default=str,
)}

Structured operational facts:

{json.dumps(
    facts,
    ensure_ascii=False,
    default=str,
)}
"""

    state["classification_prompt"] = (
        prompt
    )

    try:

        llm = _get_llm()

        call_id = new_id(
            "llm"
        )

        response = llm.invoke(
            prompt
        )

        content = (
            response.content
            if hasattr(
                response,
                "content",
            )
            else str(response)
        )

        state["classification_response"] = (
            content
        )

        state["llm_call_id"] = (
            call_id
        )

        try:

            classification = json.loads(
                content
            )

        except json.JSONDecodeError:

            classification = {
                "severity": (
                    str(
                        ticket_severity
                        or "MEDIUM"
                    ).upper()
                ),
                "category": "OTHER",
                "reason": (
                    "LLM returned non-JSON "
                    "classification."
                ),
            }

        # -----------------------------------------------------
        # Preserve ticket severity when present.
        # -----------------------------------------------------

        if ticket_severity:

            severity = str(
                ticket_severity
            ).upper()

        else:

            severity = str(
                classification.get(
                    "severity",
                    "MEDIUM",
                )
            ).upper()

        category = str(
            classification.get(
                "category",
                "OTHER",
            )
        ).upper()

        if severity not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:

            severity = "MEDIUM"

        if category not in {
            "BREAKDOWN",
            "DELAY",
            "MAINTENANCE",
            "OTHER",
        }:

            category = "OTHER"

        classification = {
            "severity":
                severity,

            "category":
                category,

            "reason":
                str(
                    classification.get(
                        "reason",
                        "",
                    )
                )[:500],
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

        fallback_severity = str(
            ticket_severity
            or "MEDIUM"
        ).upper()

        if fallback_severity not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:

            fallback_severity = "MEDIUM"

        classification = {
            "severity":
                fallback_severity,

            "category":
                "BREAKDOWN",

            "reason":
                (
                    "LLM classification unavailable; "
                    "safe fallback used."
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
        or (
            state.get("vehicle") or {}
        ).get("home_hub")
    )

    destination = (
        ticket.get("destination")
        or ticket.get("destination_name")
        or ""
    )

    client = _ticket_client(
        ticket
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    # tickets.json uses `km_from_origin_hub`.
    # ---------------------------------------------------------

    raw_distance = ticket.get(
        "km_from_origin_hub"
    )

    try:

        breakdown_distance = float(
            raw_distance
            if raw_distance is not None
            else 999999
        )

    except (
        TypeError,
        ValueError,
    ):

        breakdown_distance = 999999

    # ---------------------------------------------------------
    # Origin hub is the candidate source.
    # The rules engine independently records the
    # <=50km replacement rule.
    # ---------------------------------------------------------

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
                ORDER BY vehicle_id
                """,
                (candidate_hub,),
            ).fetchall()

        else:

            rows = db.execute(
                """
                SELECT *
                FROM vehicles
                WHERE status = 'Active'
                ORDER BY vehicle_id
                """
            ).fetchall()

    candidates = [
        dict(row)
        for row in rows
    ]

    state["candidate_vehicles"] = (
        candidates
    )

    # ---------------------------------------------------------
    # Ticket date
    # ---------------------------------------------------------

    ticket_date = (
        _safe_date(
            ticket.get("date")
        )
        or _safe_date(
            ticket.get("created_at")
        )
        or date.today()
    )

    # ---------------------------------------------------------
    # Context for deterministic rules
    # ---------------------------------------------------------

    trip_context = {

        "client":
            client,

        "destination":
            destination,

        "destination_region":
            ticket.get(
                "destination_region",
                destination,
            ),

        "origin_hub":
            origin_hub,

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

    # ---------------------------------------------------------
    # Evaluate candidates
    # ---------------------------------------------------------

    eligible = []
    checked_rules = []

    for candidate in candidates:

        eligible_flag, rules = evaluate(
            vehicle=candidate,
            trip_context=trip_context,
            driver=state.get("driver"),
            today=ticket_date,
        )

        checked_rules.extend(
            rules
        )

        if eligible_flag:

            eligible.append(
                candidate
            )

    checked_rules = list(
        dict.fromkeys(
            checked_rules
        )
    )

    state["eligible_vehicles"] = (
        eligible
    )

    state["checked_rule_ids"] = (
        checked_rules
    )

    # ---------------------------------------------------------
    # No eligible vehicle
    # ---------------------------------------------------------

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

                "eligible_count":
                    0,

                "checked_rule_ids":
                    checked_rules,
            },
            rule_ids=checked_rules,
        )

        return state

    # ---------------------------------------------------------
    # Deterministic selection
    # ---------------------------------------------------------

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
                selected.get(
                    "vehicle_id"
                ),

            "vehicle_reg":
                selected.get(
                    "registration_number"
                ),

            "candidate_count":
                len(candidates),

            "eligible_count":
                len(eligible),
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

    ticket_id = state[
        "ticket_id"
    ]

    # ---------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------

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
                    existing[
                        "work_order_id"
                    ]
            },
        )

        return state

    # ---------------------------------------------------------
    # Create standardized work order
    # ---------------------------------------------------------

    work_order_id = new_id(
        "WO"
    )

    selected = (
        state.get(
            "selected_vehicle"
        )
        or {}
    )

    work_order = {

        "work_order_id":
            work_order_id,

        "ticket_id":
            ticket_id,

        "vehicle_reg":
            selected.get(
                "registration_number"
            )
            or selected.get(
                "vehicle_reg"
            ),

        "created_at":
            utc_now(),

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
    }

    # ---------------------------------------------------------
    # Idempotent output
    # ---------------------------------------------------------

    appended = _append_unique_jsonl(
        OUTPUT_DIR
        / "work_orders.jsonl",
        work_order,
        "ticket_id",
    )

    # ---------------------------------------------------------
    # Ledger
    # ---------------------------------------------------------

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
        (
            "created"
            if appended
            else "existing_output_reused"
        ),
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

    ticket_id = state[
        "ticket_id"
    ]

    # ---------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------

    existing = get_pipeline_state(
        ticket_id
    )

    if (
        existing
        and existing["notification_id"]
    ):

        state["notification_id"] = (
            existing[
                "notification_id"
            ]
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

    ticket = state[
        "ticket"
    ]

    client = (
        _ticket_client(
            ticket
        )
        or "the client"
    )

    work_order = (
        state.get(
            "work_order"
        )
        or {}
    )

    selected_vehicle = (
        state.get(
            "selected_vehicle"
        )
        or {}
    )

    classification = (
        state.get(
            "classification"
        )
        or {}
    )

    citations = [
        {
            "rule_id":
                rule_id
        }
        for rule_id
        in state.get(
            "checked_rule_ids",
            [],
        )
    ]

    # ---------------------------------------------------------
    # Draft prompt
    # ---------------------------------------------------------

    prompt = f"""
Draft a concise professional logistics
message to {client}.

This is a DRAFT awaiting human approval.

Never claim that the message was sent.

Do not include personal data such as:

- phone numbers
- Aadhaar numbers
- driving licence numbers
- private contact information

Use only operational information relevant
to the client.

Ticket:

{json.dumps(
    ticket,
    ensure_ascii=False,
    default=str,
)}

Work order:

{json.dumps(
    work_order,
    ensure_ascii=False,
    default=str,
)}

Selected vehicle:

{json.dumps(
    selected_vehicle,
    ensure_ascii=False,
    default=str,
)}

Classification:

{json.dumps(
    classification,
    ensure_ascii=False,
    default=str,
)}

Rules:

{json.dumps(
    citations,
    ensure_ascii=False,
    default=str,
)}

Write only the message body.
"""

    try:

        llm = _get_llm()

        call_id = new_id(
            "llm"
        )

        response = llm.invoke(
            prompt
        )

        message = (
            response.content
            if hasattr(
                response,
                "content",
            )
            else str(response)
        )

    except Exception as exc:

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

        _audit(
            state,
            "draft_notification_node",
            "llm_failed_fallback",
            {
                "error":
                    str(exc),
            },
        )

    # ---------------------------------------------------------
    # Pending notification
    # ---------------------------------------------------------

    notification_id = new_id(
        "COM"
    )

    notification = {

        "message_id":
            notification_id,

        "ticket_id":
            ticket_id,

        "recipient":
            client,

        "body":
            message.strip(),

        "context": {

            "work_order_id":
                state.get(
                    "work_order_id"
                ),

            "vehicle_reg":
                selected_vehicle.get(
                    "registration_number"
                ),

            "classification":
                classification,
        },

        "citations":
            citations,

        "status":
            "PENDING_APPROVAL",

        "created_at":
            utc_now(),
    }

    # ---------------------------------------------------------
    # Idempotent pending output
    # ---------------------------------------------------------

    appended = _append_unique_jsonl(
        OUTPUT_DIR
        / "comms_pending.jsonl",
        notification,
        "ticket_id",
    )

    # ---------------------------------------------------------
    # Ledger
    # ---------------------------------------------------------

    upsert_pipeline_state(
        ticket_id=ticket_id,
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
        (
            "draft_created"
            if appended
            else "existing_draft_reused"
        ),
        {
            "notification_id":
                notification_id,

            "recipient":
                client,
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

    state["current_node"] = (
        "quarantine"
    )

    reason = state.get(
        "quarantine_reason",
        "unknown validation failure",
    )

    ticket_id = state.get(
        "ticket_id"
    )

    record = {

        "ticket_id":
            ticket_id,

        "reason":
            reason,

        "status":
            "QUARANTINED",

        "created_at":
            utc_now(),
    }

    # ---------------------------------------------------------
    # Prevent duplicate quarantine records.
    # ---------------------------------------------------------

    if ticket_id:

        appended = _append_unique_jsonl(
            OUTPUT_DIR
            / "quarantine.jsonl",
            record,
            "ticket_id",
        )

    else:

        record["content_hash"] = (
            state.get(
                "content_hash"
            )
        )

        existing = read_jsonl(
            OUTPUT_DIR
            / "quarantine.jsonl"
        )

        duplicate = any(
            item.get(
                "content_hash"
            )
            == record[
                "content_hash"
            ]
            for item in existing
        )

        if duplicate:

            appended = False

        else:

            append_jsonl(
                OUTPUT_DIR
                / "quarantine.jsonl",
                record,
            )

            appended = True

    # ---------------------------------------------------------
    # Ledger
    # ---------------------------------------------------------

    if ticket_id:

        upsert_pipeline_state(
            ticket_id=ticket_id,
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
        (
            "quarantined"
            if appended
            else "already_quarantined"
        ),
        {
            "reason":
                reason,
        },
    )

    return state


# ============================================================
# AUDIT
# ============================================================

def audit_node(
    state: PipelineState,
) -> PipelineState:

    # ---------------------------------------------------------
    # Preserve the node that ran immediately before audit.
    # ---------------------------------------------------------

    previous_node = state.get(
        "current_node"
    )

    state["last_node"] = (
        previous_node
    )

    _audit(
        state,
        "audit_node",
        "pipeline_transition",
        {
            "from_node":
                previous_node,

            "status":
                state.get(
                    "status"
                ),
        },
        rule_ids=state.get(
            "checked_rule_ids",
            [],
        ),
        llm_call_id=state.get(
            "llm_call_id"
        ),
    )

    # IMPORTANT:
    # Do not set current_node = "audit".
    #
    # graph.py uses last_node to determine
    # the next transition.

    return state

