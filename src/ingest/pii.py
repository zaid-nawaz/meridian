from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any


PII_SALT = "meridian-pii-v1"


PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)

AADHAAR_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)"
)

DL_PATTERN = re.compile(
    r"(?<![A-Z0-9])"
    r"(?:[A-Z]{2}[\s-]?\d{2}"
    r"[\s-]?\d{4}"
    r"[\s-]?\d{5,7})"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)


def _pseudonymize(value: Any, field_type: str) -> str:
    """
    Convert a sensitive value into a deterministic pseudonymous token.

    The same value + field type always produces the same token.
    """

    raw = str(value).strip()

    digest = hashlib.sha256(
        f"{PII_SALT}:{field_type}:{raw}".encode("utf-8")
    ).hexdigest()

    return f"{field_type}-{digest[:8]}"


def mask_record(
    record: dict,
    field_map: dict,
) -> dict:
    """
    Return a copy of a record with sensitive fields masked.

    Example:

        record = {
            "name": "Rahul",
            "phone": "+91 9876543210",
        }

        field_map = {
            "phone": "PHN",
        }

    becomes something like:

        {
            "name": "Rahul",
            "phone": "PHN-a1b2c3d4",
        }
    """

    masked = deepcopy(record)

    for field_name, field_type in field_map.items():
        if field_name not in masked:
            continue

        value = masked[field_name]

        if value is None:
            continue

        if str(value).strip() == "":
            continue

        masked[field_name] = _pseudonymize(
            value=value,
            field_type=field_type,
        )

    return masked


def scan_for_leaks(text: str) -> list[str]:
    """
    Scan text for raw PII patterns.

    Returns a list describing the types of PII detected.
    """

    leaks: list[str] = []

    if PHONE_PATTERN.search(text):
        leaks.append("phone")

    if AADHAAR_PATTERN.search(text):
        leaks.append("aadhaar")

    if DL_PATTERN.search(text):
        leaks.append("dl_number")

    return leaks