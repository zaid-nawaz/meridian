from __future__ import annotations

from src.ingest.database import get_connection
from src.ingest.entity_resolution import normalize_plate


def get_vehicle(
    registration: str,
) -> dict | None:
    """
    Retrieve a vehicle by registration number.
    """

    normalized = normalize_plate(
        registration
    )

    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                vehicle_id,
                registration_number,
                model,
                model_year,
                bs_stage,
                engine_heater,
                home_hub,
                capacity_tonnes,
                status
            FROM vehicles
            WHERE normalized_registration = ?
            """,
            (normalized,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_driver(
    driver_id: str,
) -> dict | None:
    """
    Retrieve a driver by driver ID.
    """

    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                driver_id,
                driver_name,
                joining_date,
                tenure_months,
                home_hub,
                status
            FROM drivers
            WHERE driver_id = ?
            """,
            (driver_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_vehicle_trips(
    registration: str,
    limit: int = 20,
) -> list[dict]:
    """
    Retrieve recent trips for a vehicle.
    """

    normalized = normalize_plate(
        registration
    )

    with get_connection() as db:

        rows = db.execute(
            """
            SELECT
                trip_id,
                created_at,
                origin_name,
                dest_name,
                dispatch_time,
                delivery_time,
                osrm_distance_km,
                osrm_time_min,
                actual_time_min,
                driver_id,
                client,
                status,
                billed_amount
            FROM trips
            WHERE normalized_vehicle_reg = ?
            ORDER BY dispatch_time DESC
            LIMIT ?
            """,
            (
                normalized,
                limit,
            ),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_vehicle_maintenance(
    registration: str,
    limit: int = 20,
) -> list[dict]:
    """
    Retrieve recent maintenance events.
    """

    normalized = normalize_plate(
        registration
    )

    with get_connection() as db:

        rows = db.execute(
            """
            SELECT
                service_date,
                vehicle_reg,
                odometer_km,
                mechanic,
                note
            FROM maintenance_events
            WHERE normalized_vehicle_reg = ?
            ORDER BY service_date DESC
            LIMIT ?
            """,
            (
                normalized,
                limit,
            ),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def get_client_trip_summary(
    client: str,
) -> dict | None:
    """
    Return basic trip statistics for a client.
    """

    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                client,
                COUNT(*) AS total_trips,
                SUM(
                    CASE
                        WHEN status = 'COMPLETED'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_trips,
                SUM(billed_amount)
                    AS total_billed_amount
            FROM trips
            WHERE normalized_client = ?
            GROUP BY normalized_client
            """,
            (client,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)