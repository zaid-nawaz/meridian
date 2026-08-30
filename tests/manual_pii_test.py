from src.ingest.pii import mask_record, scan_for_leaks


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

print("Original:")
print(record)

print("\nMasked:")
print(masked)

print("\nLeak scan:")
print(scan_for_leaks(str(masked)))