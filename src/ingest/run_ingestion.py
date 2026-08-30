from __future__ import annotations

from src.ingest.database import initialize_database
from src.ingest.load_dispatcher_interview import (
    load_dispatcher_interview,
)
from src.ingest.load_drivers import load_drivers
from src.ingest.load_emails import load_emails
from src.ingest.load_fleet import load_fleet
from src.ingest.load_maintenance import (
    load_maintenance,
)
from src.ingest.load_trips import load_trips


def count_table(table_name: str) -> int:
    """
    Return the number of rows in a SQLite table.
    """

    from src.ingest.database import get_connection

    with get_connection() as connection:

        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM {table_name}"
        ).fetchone()

        return row["count"]


def run_ingestion() -> None:
    """
    Run the complete static-data ingestion pipeline.
    """

    print("=" * 60)
    print("MERIDIAN STATIC INGESTION")
    print("=" * 60)

    print("\n[1/6] Initializing database...")
    initialize_database()
    print("Database ready.")

    print("\n[2/6] Loading fleet...")
    fleet_count = load_fleet()
    print(f"Loaded {fleet_count} vehicles.")

    print("\n[3/6] Loading drivers...")
    driver_count = load_drivers()
    print(f"Loaded {driver_count} drivers.")

    print("\n[4/6] Loading trips...")
    trip_count = load_trips()
    print(f"Loaded {trip_count} trips.")

    print("\n[5/6] Loading maintenance...")
    maintenance_count = load_maintenance()
    print(
        f"Loaded {maintenance_count} maintenance events."
    )

    print("\n[6/6] Loading text corpora...")

    email_count = load_emails()

    interview_count = load_dispatcher_interview()

    print(
        f"Loaded {email_count} email chunks."
    )

    print(
        f"Loaded {interview_count} "
        "dispatcher interview chunks."
    )

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)

    tables = [
        "vehicles",
        "drivers",
        "clients",
        "trips",
        "maintenance_events",
    ]

    for table in tables:

        print(
            f"{table:25} "
            f"{count_table(table):>8}"
        )

    print(
        f"{'email chunks':25} "
        f"{email_count:>8}"
    )

    print(
        f"{'interview chunks':25} "
        f"{interview_count:>8}"
    )

    print("=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()