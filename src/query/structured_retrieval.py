from __future__ import annotations

from src.query.evidence import (
    Citation,
    Evidence,
    EvidencePack,
)
from src.retrieval.sql_queries import (
    get_driver,
    get_vehicle,
    get_vehicle_maintenance,
    get_vehicle_trips,
)
from src.query.router import QueryRoute


def retrieve_structured(
    query: str,
    route: QueryRoute,
) -> EvidencePack:

    pack = EvidencePack(query=query)

    if route.route == "vehicle":

        if not route.vehicle_registration:
            return pack

        vehicle = get_vehicle(
            route.vehicle_registration
        )

        if vehicle is None:
            return pack

        citation = Citation(
            citation_id="sql-vehicle-1",
            source_type="sql",
            source="vehicles",
            location=(
                f"vehicle_id={vehicle['vehicle_id']}"
            ),
            description=(
                "Vehicle master record"
            ),
        )

        pack.add(
            Evidence(
                evidence_id="vehicle-1",
                source_type="sql",
                content=vehicle,
                relevance=1.0,
                citation=citation,
            )
        )

    elif route.route == "vehicle_trips":

        if not route.vehicle_registration:
            return pack

        vehicle = get_vehicle(
            route.vehicle_registration
        )

        trips = get_vehicle_trips(
            route.vehicle_registration,
            limit=10,
        )

        if vehicle:

            pack.add(
                Evidence(
                    evidence_id="vehicle-1",
                    source_type="sql",
                    content=vehicle,
                    relevance=1.0,
                    citation=Citation(
                        citation_id="sql-vehicle-1",
                        source_type="sql",
                        source="vehicles",
                        location=(
                            f"vehicle_id="
                            f"{vehicle['vehicle_id']}"
                        ),
                        description=(
                            "Vehicle master record"
                        ),
                    ),
                )
            )

        if trips:

            pack.add(
                Evidence(
                    evidence_id="trips-1",
                    source_type="sql",
                    content=trips,
                    relevance=0.95,
                    citation=Citation(
                        citation_id="sql-trips-1",
                        source_type="sql",
                        source="trips",
                        location=(
                            "normalized_vehicle_reg="
                            f"{vehicle['registration_number']}"
                            if vehicle
                            else route.vehicle_registration
                        ),
                        description=(
                            "Recent trips for vehicle"
                        ),
                    ),
                )
            )

    elif route.route == "vehicle_maintenance":

        if not route.vehicle_registration:
            return pack

        vehicle = get_vehicle(
            route.vehicle_registration
        )

        maintenance = get_vehicle_maintenance(
            route.vehicle_registration,
            limit=20,
        )

        if vehicle:

            pack.add(
                Evidence(
                    evidence_id="vehicle-1",
                    source_type="sql",
                    content=vehicle,
                    relevance=1.0,
                    citation=Citation(
                        citation_id="sql-vehicle-1",
                        source_type="sql",
                        source="vehicles",
                        location=(
                            f"vehicle_id="
                            f"{vehicle['vehicle_id']}"
                        ),
                        description=(
                            "Vehicle master record"
                        ),
                    ),
                )
            )

        if maintenance:

            pack.add(
                Evidence(
                    evidence_id="maintenance-1",
                    source_type="sql",
                    content=maintenance,
                    relevance=0.98,
                    citation=Citation(
                        citation_id="sql-maintenance-1",
                        source_type="sql",
                        source="maintenance_events",
                        location=(
                            "normalized_vehicle_reg="
                            f"{route.vehicle_registration}"
                        ),
                        description=(
                            "Vehicle maintenance history"
                        ),
                    ),
                )
            )

    elif route.route == "driver":

        if not route.driver_id:
            return pack

        driver = get_driver(
            route.driver_id
        )

        if driver is None:
            return pack

        pack.add(
            Evidence(
                evidence_id="driver-1",
                source_type="sql",
                content=driver,
                relevance=1.0,
                citation=Citation(
                    citation_id="sql-driver-1",
                    source_type="sql",
                    source="drivers",
                    location=(
                        f"driver_id={driver['driver_id']}"
                    ),
                    description=(
                        "Driver roster record"
                    ),
                ),
            )
        )

    return pack