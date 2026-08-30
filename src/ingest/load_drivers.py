from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingest.database import get_connection
from src.ingest.pii import mask_record
from src.ingest.utils import calculate_tenure_months


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DRIVERS_PATH = (
    PROJECT_ROOT
    / "data"
    / "static"
    / "drivers_roster.csv"
)


PII_FIELDS = {
    "phone": "PHN",
    "dl_number": "DL",
    "aadhaar": "AAD",
}


def load_drivers() -> int:
    """
    Load drivers_roster.csv.

    Sensitive fields are pseudonymized before being inserted
    into SQLite.
    """

    if not DRIVERS_PATH.exists():
        raise FileNotFoundError(
            f"Driver file not found: {DRIVERS_PATH}"
        )

    df = pd.read_csv(DRIVERS_PATH)

    required_columns = {
        "driver_id",
        "name",
        "phone",
        "dl_number",
        "aadhaar",
        "joining_date",
        "home_hub",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Driver file is missing columns: {sorted(missing)}"
        )

    inserted = 0

    with get_connection() as connection:

        for _, row in df.iterrows():

            record = row.to_dict()

            masked = mask_record(
                record,
                PII_FIELDS,
            )

            joining_date = str(
                row["joining_date"]
            ).strip()

            tenure_months = calculate_tenure_months(
                joining_date
            )

            connection.execute(
                """
                INSERT OR REPLACE INTO drivers (
                    driver_id,
                    driver_name,
                    phone,
                    dl_number,
                    aadhaar,
                    joining_date,
                    tenure_months,
                    home_hub
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row["driver_id"]).strip(),
                    str(row["name"]).strip(),
                    masked["phone"],
                    masked["dl_number"],
                    masked["aadhaar"],
                    joining_date,
                    tenure_months,
                    "active",
                ),
            )

            inserted += 1

        connection.commit()

    return inserted


if __name__ == "__main__":
    count = load_drivers()

    print(f"Loaded {count} drivers.")