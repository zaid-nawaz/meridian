from __future__ import annotations

import re


# ============================================================
# PLATE NORMALIZATION
# ============================================================

def normalize_plate(raw: str) -> str:
    """
    Normalize a vehicle registration number.

    Examples:

        UP-40-IM-3144
        UP40IM3144
        up40im3144
        UP 40 IM 3144

    ->

        UP40IM3144
    """

    if raw is None:
        return ""

    value = str(raw).strip().upper()

    return re.sub(r"[^A-Z0-9]", "", value)


# ============================================================
# CLIENT NORMALIZATION
# ============================================================

CLIENT_ALIASES: dict[str, str] = {}


def normalize_client_name(raw: str) -> str:
    """
    Normalize a client name.

    Basic normalization:

    - strips whitespace
    - uppercases
    - collapses repeated spaces
    - removes periods and commas
    - applies known aliases
    """

    if raw is None:
        return ""

    value = str(raw).strip().upper()

    value = re.sub(r"\s+", " ", value)

    value = re.sub(r"[.,]", "", value)

    return CLIENT_ALIASES.get(value, value)


def add_client_alias(
    alias: str,
    canonical_name: str,
) -> None:
    """
    Register a client alias.
    """

    normalized_alias = normalize_client_name(alias)

    normalized_canonical = normalize_client_name(
        canonical_name
    )

    CLIENT_ALIASES[normalized_alias] = normalized_canonical