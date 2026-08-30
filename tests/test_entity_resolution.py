from src.ingest.entity_resolution import (
    normalize_client_name,
    normalize_plate,
)


def test_plate_normalization():
    assert normalize_plate("UP-40-IM-3144") == "UP40IM3144"

    assert normalize_plate("UP40IM3144") == "UP40IM3144"

    assert normalize_plate("up40im3144") == "UP40IM3144"

    assert normalize_plate("UP 40 IM 3144") == "UP40IM3144"


def test_plate_variants_are_equal():
    variants = [
        "UP-40-IM-3144",
        "UP40IM3144",
        "up40im3144",
        "UP 40 IM 3144",
    ]

    normalized = {
        normalize_plate(value)
        for value in variants
    }

    assert len(normalized) == 1


def test_empty_plate():
    assert normalize_plate("") == ""

    assert normalize_plate(None) == ""


def test_client_normalization():
    assert normalize_client_name("Shakti Cement") == "SHAKTI CEMENT"

    assert normalize_client_name("  Shakti Cement  ") == "SHAKTI CEMENT"

    assert normalize_client_name("SHAKTI CEMENT") == "SHAKTI CEMENT"


def test_client_punctuation():
    assert normalize_client_name("Shakti Cement.") == "SHAKTI CEMENT"

    assert normalize_client_name("Shakti, Cement") == "SHAKTI CEMENT"