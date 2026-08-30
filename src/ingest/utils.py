from __future__ import annotations

from datetime import date, datetime
from typing import Any


def clean_string(value: Any) -> str | None:
    """
    Convert a value into a clean string.

    Empty values become None.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def calculate_tenure_months(
    joining_date: str,
    reference_date: date | None = None,
) -> float:
    """
    Calculate approximate driver tenure in months.

    We use days / 30.44 rather than simply subtracting months
    so that the result is reasonably accurate.
    """

    if reference_date is None:
        reference_date = date.today()

    joined = datetime.strptime(
        joining_date,
        "%Y-%m-%d",
    ).date()

    days = (reference_date - joined).days

    return round(days / 30.44, 2)