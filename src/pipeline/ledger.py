from __future__ import annotations

from src.ingest.database import get_connection


def get_pipeline_state(
    ticket_id: str,
) -> dict | None:

    with get_connection() as db:

        row = db.execute(
            """
            SELECT
                ticket_id,
                content_hash,
                status,
                work_order_id,
                notification_id,
                updated_at
            FROM pipeline_state
            WHERE ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()

    return dict(row) if row else None


def upsert_pipeline_state(
    ticket_id: str,
    content_hash: str,
    status: str,
    work_order_id: str | None = None,
    notification_id: str | None = None,
) -> None:

    with get_connection() as db:

        db.execute(
            """
            INSERT INTO pipeline_state (
                ticket_id,
                content_hash,
                status,
                work_order_id,
                notification_id
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(ticket_id)
            DO UPDATE SET
                content_hash = excluded.content_hash,
                status = excluded.status,
                work_order_id =
                    COALESCE(
                        excluded.work_order_id,
                        pipeline_state.work_order_id
                    ),
                notification_id =
                    COALESCE(
                        excluded.notification_id,
                        pipeline_state.notification_id
                    ),
                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                ticket_id,
                content_hash,
                status,
                work_order_id,
                notification_id,
            ),
        )


def get_work_order(
    ticket_id: str,
) -> dict | None:

    state = get_pipeline_state(
        ticket_id
    )

    if not state:
        return None

    if not state["work_order_id"]:
        return None

    return {
        "work_order_id":
            state["work_order_id"],
        "ticket_id":
            state["ticket_id"],
    }