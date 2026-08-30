from src.retrieval.sql_queries import (
    get_vehicle,
    get_vehicle_maintenance,
    get_vehicle_trips,
)


def test_get_vehicle():

    vehicle = get_vehicle(
        "RJ-43-DD-3546"
    )

    assert vehicle is not None

    assert (
        vehicle["registration_number"]
        == "RJ43DD3546"
    )


def test_vehicle_registration_normalization():

    vehicle = get_vehicle(
        "rj 43 dd 3546"
    )

    assert vehicle is not None

    assert (
        vehicle["registration_number"]
        == "RJ43DD3546"
    )


def test_vehicle_trips():

    trips = get_vehicle_trips(
        "RJ43DD3546",
        limit=5,
    )

    assert isinstance(
        trips,
        list,
    )


def test_vehicle_maintenance():

    maintenance = get_vehicle_maintenance(
        "RJ43DD3546",
        limit=5,
    )

    assert isinstance(
        maintenance,
        list,
    )