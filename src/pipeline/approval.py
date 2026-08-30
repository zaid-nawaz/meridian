from __future__ import annotations

from src.pipeline.utils import (
    OUTPUT_DIR,
    append_jsonl,
    read_jsonl,
    utc_now,
)


PENDING_PATH = (
    OUTPUT_DIR
    / "comms_pending.jsonl"
)

SENT_PATH = (
    OUTPUT_DIR
    / "comms_sent.jsonl"
)


def approve_pending() -> None:

    pending = read_jsonl(
        PENDING_PATH
    )

    if not pending:

        print(
            "No pending communications."
        )

        return

    remaining = []

    for item in pending:

        print("\n" + "=" * 60)

        print(
            "Notification:",
            item.get(
                "notification_id"
            ),
        )

        print(
            "Ticket:",
            item.get(
                "ticket_id"
            ),
        )

        print(
            "Client:",
            item.get(
                "client"
            ),
        )

        print("\nMESSAGE:")
        print(
            item.get(
                "message",
                "",
            )
        )

        print("\nCITATIONS:")

        for citation in item.get(
            "citations",
            [],
        ):

            print(
                " -",
                citation,
            )

        answer = input(
            "\nApprove? [y/N]: "
        ).strip().lower()

        if answer == "y":

            sent = {
                **item,
                "status": "SENT",
                "approved_by": "cli_user",
                "sent_at": utc_now(),
            }

            append_jsonl(
                SENT_PATH,
                sent,
            )

            print(
                "Approved."
            )

        else:

            remaining.append(
                item
            )

            print(
                "Left pending."
            )

    with PENDING_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        for item in remaining:

            import json

            file.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
                + "\n"
            )


if __name__ == "__main__":
    approve_pending()