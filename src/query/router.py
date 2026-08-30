from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class QueryRoute:
    """
    Result of query classification.
    """

    route: str

    vehicle_registration: str | None = None

    driver_id: str | None = None

    client: str | None = None


VEHICLE_PATTERN = re.compile(
    r"""
    \b
    (
        [A-Z]{2}
        [\s-]?
        \d{1,2}
        [\s-]?
        [A-Z]{1,3}
        [\s-]?
        \d{3,4}
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


DRIVER_PATTERN = re.compile(
    r"\bDRV-\d+\b",
    re.IGNORECASE,
)


def route_query(
    query: str,
) -> QueryRoute:
    """
    Perform lightweight query routing.

    This first version intentionally uses deterministic
    rules rather than an LLM.
    """

    text = query.strip()

    lower = text.lower()

    vehicle_match = VEHICLE_PATTERN.search(
        text
    )

    vehicle = (
        vehicle_match.group(1)
        if vehicle_match
        else None
    )

    driver_match = DRIVER_PATTERN.search(
        text
    )

    driver = (
        driver_match.group(0).upper()
        if driver_match
        else None
    )

    if vehicle:

        if any(
            word in lower
            for word in [
                "maintenance",
                "repair",
                "mechanic",
                "service",
                "issue",
                "problem",
                "breakdown",
            ]
        ):
            return QueryRoute(
                route="vehicle_maintenance",
                vehicle_registration=vehicle,
            )

        if any(
            word in lower
            for word in [
                "trip",
                "trips",
                "journey",
                "delivery",
                "deliveries",
                "route",
            ]
        ):
            return QueryRoute(
                route="vehicle_trips",
                vehicle_registration=vehicle,
            )

        return QueryRoute(
            route="vehicle",
            vehicle_registration=vehicle,
        )

    if driver:

        return QueryRoute(
            route="driver",
            driver_id=driver,
        )

    if any(
        word in lower
        for word in [
            "email",
            "emails",
            "dispatcher",
            "interview",
            "policy",
            "rule",
        ]
    ):

        return QueryRoute(
            route="semantic",
        )

    return QueryRoute(
        route="semantic",
    )