from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.database import get_connection
from src.ingest.entity_resolution import normalize_plate


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MAINTENANCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "maintenance_log.xlsx"
)


def load_maintenance() -> int:
    """
    Load maintenance_log.xlsx into SQLite.
    """

    if not MAINTENANCE_PATH.exists():
        raise FileNotFoundError(
            f"Maintenance file not found: {MAINTENANCE_PATH}"
        )

    df = pd.read_excel(MAINTENANCE_PATH)

    required_columns = {
        "date",
        "vehicle",
        "odometer_km",
        "mechanic",
        "notes",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "Maintenance file is missing columns: "
            f"{sorted(missing)}"
        )

    inserted = 0

    with get_connection() as connection:

        for _, row in df.iterrows():

            vehicle_reg = str(
                row["vehicle"]
            ).strip()

            normalized_vehicle = normalize_plate(
                vehicle_reg
            )

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

            connection.execute(
                """
                INSERT INTO maintenance_events (
                    service_date,
                    vehicle_reg,
                    normalized_vehicle_reg,
                    vehicle_id,
                    odometer_km,
                    mechanic,
                    note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["date"]),
                    vehicle_reg,
                    normalized_vehicle,
                    vehicle_id,
                    row["odometer_km"],
                    row["mechanic"],
                    row["notes"],
                ),
            )

            inserted += 1

        connection.commit()

    return inserted


if __name__ == "__main__":
    count = load_maintenance()

    print(
        f"Loaded {count} maintenance events."
    )