from src.query.router import route_query


def test_vehicle_query():

    route = route_query(
        "What model is RJ43DD3546?"
    )

    assert route.route == "vehicle"

    assert (
        route.vehicle_registration
        == "RJ43DD3546"
    )


def test_vehicle_trip_query():

    route = route_query(
        "Show me trips for RJ-43-DD-3546"
    )

    assert route.route == "vehicle_trips"


def test_vehicle_maintenance_query():

    route = route_query(
        "What maintenance issues did "
        "RJ43DD3546 have?"
    )

    assert (
        route.route
        == "vehicle_maintenance"
    )


def test_driver_query():

    route = route_query(
        "Tell me about DRV-022"
    )

    assert route.route == "driver"

    assert route.driver_id == "DRV-022"


def test_semantic_query():

    route = route_query(
        "What are the rules for night runs?"
    )

    assert route.route == "semantic"