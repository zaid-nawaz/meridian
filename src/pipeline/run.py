from __future__ import annotations

import json
import sys
from pathlib import Path

from src.pipeline.graph import build_graph


ROOT = Path(__file__).resolve().parents[2]

TICKETS_PATH = (
    ROOT
    / "data"
    / "live"
    / "tickets.json"
)


def load_tickets(
    path: Path,
) -> list[dict]:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        if "tickets" in data:
            return data["tickets"]

    raise ValueError(
        "tickets.json must contain a list "
        "or {'tickets': [...]}"
    )


def run(
    tickets_path: Path = TICKETS_PATH,
) -> None:

    tickets = load_tickets(
        tickets_path
    )

    graph = build_graph()

    print("=" * 60)
    print("MERIDIAN PIPELINE")
    print("=" * 60)

    for index, ticket in enumerate(
        tickets,
        start=1,
    ):

        ticket_id = ticket.get(
            "ticket_id",
            f"unknown-{index}",
        )

        print(
            f"\n[{index}/{len(tickets)}] "
            f"{ticket_id}"
        )

        state = {
            "ticket": ticket,
            "maintenance": [],
            "candidate_vehicles": [],
            "eligible_vehicles": [],
            "checked_rule_ids": [],
            "audit_events": [],
        }

        try:

            result = graph.invoke(
                state
            )

            print(
                "  status:",
                result.get("status"),
            )

            if result.get(
                "work_order_id"
            ):
                print(
                    "  work order:",
                    result[
                        "work_order_id"
                    ],
                )

            if result.get(
                "quarantine_reason"
            ):
                print(
                    "  quarantine:",
                    result[
                        "quarantine_reason"
                    ],
                )

        except Exception as exc:

            print(
                f"  ERROR: {exc}"
            )

    print("\nPipeline complete.")


if __name__ == "__main__":

    path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else TICKETS_PATH
    )

    run(path)