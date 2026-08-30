from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.database import get_connection
from src.ingest.entity_resolution import normalize_plate


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FLEET_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "fleet_master.csv"
)


def load_fleet() -> int:
    """
    Load fleet_master.csv into the vehicles table.

    Returns the number of inserted vehicles.
    """

    if not FLEET_PATH.exists():
        raise FileNotFoundError(
            f"Fleet file not found: {FLEET_PATH}"
        )

    df = pd.read_csv(FLEET_PATH)

    required_columns = {
        "vehicle_id",
        "registration_number",
        "model",
        "year",
        "bs_stage",
        "engine_heater",
        "home_hub",
        "capacity_tonnes",
        "status",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Fleet file is missing columns: {sorted(missing)}"
        )

    inserted = 0

    with get_connection() as connection:

        for _, row in df.iterrows():

            registration = str(
                row["registration_number"]
            ).strip()

            normalized_registration = normalize_plate(
                registration
            )

            connection.execute(
                """
                INSERT OR REPLACE INTO vehicles (
                    vehicle_id,
                    registration_number,
                    normalized_registration,
                    model,
                    model_year,
                    bs_stage,
                    engine_heater,
                    home_hub,
                    capacity_tonnes,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["vehicle_id"]).strip(),
                    registration,
                    normalized_registration,
                    row["model"],
                    int(row["year"]),
                    row["bs_stage"],
                    row["engine_heater"],
                    row["home_hub"],
                    float(row["capacity_tonnes"]),
                    row["status"],
                ),
            )

            inserted += 1

        connection.commit()

    return inserted


if __name__ == "__main__":
    count = load_fleet()

    print(f"Loaded {count} vehicles.")