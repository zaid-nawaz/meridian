from src.ingest.pii import mask_record, scan_for_leaks


def test_mask_record_removes_raw_pii():
    record = {
        "name": "Rahul Kumar",
        "phone": "+91 9876543210",
        "dl_number": "DL-04201123456",
        "aadhaar": "1234 5678 9012",
    }

    field_map = {
        "phone": "PHN",
        "dl_number": "DL",
        "aadhaar": "AAD",
    }

    masked = mask_record(record, field_map)

    assert masked["name"] == "Rahul Kumar"

    assert masked["phone"] != record["phone"]
    assert masked["dl_number"] != record["dl_number"]
    assert masked["aadhaar"] != record["aadhaar"]

    assert scan_for_leaks(str(masked)) == []


def test_masking_is_deterministic():
    record = {
        "phone": "+91 9876543210",
        "dl_number": "DL-04201123456",
        "aadhaar": "123456789012",
    }

    field_map = {
        "phone": "PHN",
        "dl_number": "DL",
        "aadhaar": "AAD",
    }

    first = mask_record(record, field_map)
    second = mask_record(record, field_map)

    assert first == second


def test_different_values_get_different_tokens():
    record_a = {
        "phone": "+91 9876543210",
    }

    record_b = {
        "phone": "+91 9876543211",
    }

    field_map = {
        "phone": "PHN",
    }

    masked_a = mask_record(record_a, field_map)
    masked_b = mask_record(record_b, field_map)

    assert masked_a["phone"] != masked_b["phone"]


def test_original_record_is_not_modified():
    record = {
        "name": "Rahul",
        "phone": "+91 9876543210",
    }

    field_map = {
        "phone": "PHN",
    }

    original_phone = record["phone"]

    mask_record(record, field_map)

    assert record["phone"] == original_phone


def test_scan_for_phone():
    text = "Driver phone: +91 9876543210"

    leaks = scan_for_leaks(text)

    assert "phone" in leaks


def test_scan_for_aadhaar():
    text = "Aadhaar: 1234 5678 9012"

    leaks = scan_for_leaks(text)

    assert "aadhaar" in leaks


def test_scan_for_driving_license():
    text = "DL number: DL-04201123456"

    leaks = scan_for_leaks(text)

    assert "dl_number" in leaks


def test_masked_tokens_do_not_trigger_scan():
    text = """
    Driver phone: PHN-a1b2c3d4
    Aadhaar: AAD-12345678
    License: DL-abcdef12
    """

    assert scan_for_leaks(text) == []