from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.database import get_connection
from src.ingest.entity_resolution import (
    normalize_client_name,
    normalize_plate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRIPS_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "meridian_trips.csv"
)


def load_trips() -> int:
    """
    Load meridian_trips.csv into SQLite.

    Vehicle registrations and client names are normalized
    before insertion.
    """

    if not TRIPS_PATH.exists():
        raise FileNotFoundError(
            f"Trips file not found: {TRIPS_PATH}"
        )

    df = pd.read_csv(TRIPS_PATH)

    required_columns = {
        "trip_id",
        "created_at",
        "route_type",
        "origin_center",
        "origin_name",
        "dest_center",
        "dest_name",
        "dispatch_time",
        "delivery_time",
        "osrm_distance_km",
        "osrm_time_min",
        "actual_time_min",
        "vehicle_reg",
        "driver_id",
        "client",
        "status",
        "billed_amount",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Trips file is missing columns: {sorted(missing)}"
        )

    inserted = 0

    with get_connection() as connection:

        for _, row in df.iterrows():

            vehicle_reg = str(
                row["vehicle_reg"]
            ).strip()

            normalized_vehicle = normalize_plate(
                vehicle_reg
            )

            normalized_client = normalize_client_name(
                row["client"]
            )

            # Resolve vehicle.
            vehicle = connection.execute(
                """
                SELECT vehicle_id
                FROM vehicles
                WHERE normalized_registration = ?
                """,
                (normalized_vehicle,),
            ).fetchone()

            vehicle_id = (
                vehicle["vehicle_id"]
                if vehicle
                else None
            )

            # Resolve driver.
            driver_id = str(
                row["driver_id"]
            ).strip()

            driver = connection.execute(
                """
                SELECT driver_id
                FROM drivers
                WHERE driver_id = ?
                """,
                (driver_id,),
            ).fetchone()

            resolved_driver_id = (
                driver["driver_id"]
                if driver
                else None
            )

            # Create client if necessary.
            client = connection.execute(
                """
                SELECT client_id
                FROM clients
                WHERE normalized_name = ?
                """,
                (normalized_client,),
            ).fetchone()

            if client:
                client_id = client["client_id"]

            else:
                cursor = connection.execute(
                    """
                    INSERT INTO clients (
                        name,
                        normalized_name
                    )
                    VALUES (?, ?)
                    """,
                    (
                        str(row["client"]).strip(),
                        normalized_client,
                    ),
                )

                client_id = cursor.lastrowid

            connection.execute(
                """
                INSERT OR REPLACE INTO trips (
                    trip_id,
                    created_at,
                    route_type,
                    origin_center,
                    origin_name,
                    dest_center,
                    dest_name,
                    dispatch_time,
                    delivery_time,
                    osrm_distance_km,
                    osrm_time_min,
                    actual_time_min,
                    vehicle_reg,
                    normalized_vehicle_reg,
                    vehicle_id,
                    driver_id,
                    client,
                    normalized_client,
                    status,
                    billed_amount
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    str(row["trip_id"]).strip(),
                    row["created_at"],
                    row["route_type"],
                    row["origin_center"],
                    row["origin_name"],
                    row["dest_center"],
                    row["dest_name"],
                    row["dispatch_time"],
                    row["delivery_time"],
                    row["osrm_distance_km"],
                    row["osrm_time_min"],
                    row["actual_time_min"],
                    vehicle_reg,
                    normalized_vehicle,
                    vehicle_id,
                    resolved_driver_id,
                    str(row["client"]).strip(),
                    normalized_client,
                    row["status"],
                    row["billed_amount"],
                ),
            )

            inserted += 1

        connection.commit()

    return inserted


if __name__ == "__main__":
    count = load_trips()

    print(f"Loaded {count} trips.")