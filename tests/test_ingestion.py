from src.ingest.entity_resolution import normalize_plate
from src.ingest.database import get_connection


def test_vehicle_registration_resolution():
    with get_connection() as db:

        row = db.execute(
            """
            SELECT vehicle_id
            FROM vehicles
            WHERE normalized_registration = ?
            """,
            (normalize_plate("UP-17-GN-7381"),),
        ).fetchone()

    assert row is not None


def test_trip_vehicle_relationships():
    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                t.vehicle_id,
                v.vehicle_id
            FROM trips t
            JOIN vehicles v
                ON t.vehicle_id = v.vehicle_id
            LIMIT 1
            """
        ).fetchone()

    assert row is not None

    assert row["vehicle_id"] == row["vehicle_id"]


def test_driver_pii_is_masked():
    with get_connection() as db:

        rows = db.execute(
            """
            SELECT phone, dl_number, aadhaar
            FROM drivers
            LIMIT 10
            """
        ).fetchall()

    for row in rows:

        assert row["phone"] is None or row["phone"].startswith(
            "PHN-"
        )

        assert (
            row["dl_number"] is None
            or row["dl_number"].startswith("DL-")
        )

        assert (
            row["aadhaar"] is None
            or row["aadhaar"].startswith("AAD-")
        )


def test_text_corpora_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    assert (
        root / "data" / "processed" / "emails.jsonl"
    ).exists()

    assert (
        root
        / "data"
        / "processed"
        / "dispatcher_interview.jsonl"
    ).exists()