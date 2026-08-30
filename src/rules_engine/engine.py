from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RULES_PATH = (
    PROJECT_ROOT
    / "rules"
    / "dispatcher_rules.yaml"
)


def load_rules() -> list[dict]:
    """
    Load the verified dispatcher rules.
    """

    with RULES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = yaml.safe_load(file)

    return data.get("rules", [])


def _as_date(value) -> date:

    if isinstance(value, date):
        return value

    return datetime.strptime(
        str(value),
        "%Y-%m-%d",
    ).date()


def _months_between(
    start: date,
    end: date,
) -> int:

    return (end - start).days


def _is_true(value) -> bool:

    return value in {
        True,
        "true",
        "True",
        "yes",
        "Yes",
        "1",
        1,
    }


def evaluate(
    vehicle: dict | None = None,
    trip_context: dict | None = None,
    driver: dict | None = None,
    today: date | str | None = None,
) -> tuple[bool, list[str]]:

    vehicle = vehicle or {}
    trip_context = trip_context or {}
    driver = driver or {}

    if today is None:
        today = date.today()
    else:
        today = _as_date(today)

    applied_rules: list[str] = []

    # ========================================================
    # Rule 1 — BS4 Delhi/NCR
    # ========================================================

    if (
        str(vehicle.get("bs_stage", "")).upper()
        == "BS4"
    ):

        destination = str(
            trip_context.get(
                "destination_region",
                trip_context.get("destination", ""),
            )
        ).upper()

        if (
            "DELHI" in destination
            or "NCR" in destination
        ):

            if today.month in {
                10,
                11,
                12,
                1,
                2,
            }:

                applied_rules.append(
                    "BS4_DELHI_NCR_SEASONAL"
                )

                return False, applied_rules

    # ========================================================
    # Rule 2 — Hill route winter
    # ========================================================

    if (
        _is_true(
            trip_context.get("hill_route")
        )
        and today.month in {
            11,
            12,
            1,
            2,
        }
    ):

        applied_rules.append(
            "HILL_ROUTE_WINTER"
        )

        heater = _is_true(
            vehicle.get("engine_heater")
        )

        if not heater:
            return False, applied_rules

        last_brake = trip_context.get(
            "last_brake_work_date"
        )

        if last_brake:

            brake_date = _as_date(
                last_brake
            )

            days = (
                today - brake_date
            ).days

            if days <= 30:
                return False, applied_rules

    # ========================================================
    # Rule 3 — Orion Pharma
    # ========================================================

    client = str(
        trip_context.get("client", "")
    ).strip().upper()

    if client == "ORION PHARMA":

        applied_rules.append(
            "ORION_MIN_MODEL_YEAR"
        )

        try:
            model_year = int(
                vehicle.get(
                    "model_year",
                    0,
                )
            )
        except (TypeError, ValueError):
            model_year = 0

        if model_year < 2020:
            return False, applied_rules

    # ========================================================
    # Rule 4 — Service overdue
    # ========================================================

    service_due = trip_context.get(
        "service_due_date"
    )

    if service_due:

        due_date = _as_date(
            service_due
        )

        overdue_days = (
            today - due_date
        ).days

        if overdue_days > 30:

            applied_rules.append(
                "SERVICE_OVERDUE_30_DAYS"
            )

            return False, applied_rules

    # ========================================================
    # Rule 5 — New driver night run
    # ========================================================

    if (
        _is_true(
            trip_context.get("night_run")
        )
        and _is_true(
            trip_context.get(
                "solo",
                True,
            )
        )
    ):

        try:
            tenure = float(
                driver.get(
                    "tenure_months",
                    0,
                )
            )
        except (TypeError, ValueError):
            tenure = 0

        if tenure < 6:

            applied_rules.append(
                "NEW_DRIVER_NIGHT_RUN"
            )

            return False, applied_rules

    return True, applied_rules


# ============================================================
# Client SLA
# ============================================================

def get_client_sla(
    client: str,
) -> float | None:

    normalized = str(
        client
    ).strip().upper()

    if normalized == "SHAKTI CEMENT":

        return 36.0

    return None


# ============================================================
# ETA
# ============================================================

def get_eta_multiplier(
    trip_context: dict,
    trip_date: date | str,
) -> float:

    current = _as_date(
        trip_date
    )

    if current.month not in {
        7,
        8,
        9,
    }:
        return 1.0

    if _is_true(
        trip_context.get(
            "route_east_of_lucknow"
        )
    ):

        return 1.20

    return 1.0


# ============================================================
# Breakdown replacement
# ============================================================

def replacement_hub(
    trip_context: dict,
) -> str | None:

    distance = float(
        trip_context.get(
            "breakdown_distance_from_origin_km",
            999999,
        )
    )

    if distance <= 50:

        return trip_context.get(
            "origin_hub"
        )

    return None


# ============================================================
# Guddu's jugaad
# ============================================================

def get_jugaad_restriction(
    maintenance_note: str,
    maintenance_date: date | str,
    today: date | str,
) -> dict | None:

    note = str(
        maintenance_note or ""
    ).lower()

    if "jugaad" not in note:
        return None

    if (
        "permanent" not in note
        and "fix" not in note
    ):
        return None

    maintenance_day = _as_date(
        maintenance_date
    )

    current_day = _as_date(
        today
    )

    elapsed = (
        current_day - maintenance_day
    ).days

    if elapsed < 0:
        return None

    if elapsed > 7:
        return None

    return {
        "active": True,
        "days_remaining": 7 - elapsed,
        "restrict_to_home_region": True,
    }