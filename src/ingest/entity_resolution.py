from __future__ import annotations

import re


# ------------------------------------------------------------
# Plate normalization
# ------------------------------------------------------------

def normalize_plate(raw: str) -> str:
    """
    Normalize an Indian vehicle registration number.

    Examples:

        UP-40-IM-3144
        UP40IM3144
        up40im3144
        UP 40 IM 3144

    all become:

        UP40IM3144
    """

    if not raw:
        return ""

    value = str(raw).strip().upper()

    # Remove spaces, hyphens and every non-alphanumeric character.
    value = re.sub(r"[^A-Z0-9]", "", value)

    return value


# ------------------------------------------------------------
# Client normalization
# ------------------------------------------------------------

CLIENT_ALIASES: dict[str, str] = {
    # These are intentionally kept small for now.
    #
    # We will populate this from the actual datasets once
    # meridian_trips.csv and tickets.json are available.
}


def normalize_client_name(raw: str) -> str:
    """
    Normalize a client name.

    Performs basic normalization first, then checks the
    explicit alias table.
    """

    if not raw:
        return ""

    value = str(raw).strip().upper()

    # Collapse repeated whitespace.
    value = re.sub(r"\s+", " ", value)

    # Remove common punctuation.
    value = re.sub(r"[.,]", "", value)

    if value in CLIENT_ALIASES:
        return CLIENT_ALIASES[value]

    return value


def add_client_alias(
    alias: str,
    canonical_name: str,
) -> None:
    """
    Add a client alias at runtime.

    Useful when loading discovered aliases from a configuration
    source later.
    """

    normalized_alias = normalize_client_name(alias)
    normalized_canonical = normalize_client_name(canonical_name)

    CLIENT_ALIASES[normalized_alias] = normalized_canonical