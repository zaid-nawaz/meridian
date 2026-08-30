from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT / "outputs"
AUDIT_DIR = ROOT / "audit"


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def content_hash(ticket: dict) -> str:
    payload = json.dumps(
        ticket,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def append_jsonl(
    path: Path,
    record: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
            + "\n"
        )


def read_jsonl(
    path: Path,
) -> list[dict]:

    if not path.exists():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records