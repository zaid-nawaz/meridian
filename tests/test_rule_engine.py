from datetime import date

from src.rules_engine.engine import (
    evaluate,
    get_client_sla,
    get_eta_multiplier,
    get_jugaad_restriction,
    load_rules,
    replacement_hub,
)


def test_rules_yaml_loads():

    rules = load_rules()

    assert len(rules) >= 11

    rule_ids = {
        rule["rule_id"]
        for rule in rules
    }

    assert (
        "BS4_DELHI_NCR_SEASONAL"
        in rule_ids
    )

    assert (
        "HILL_ROUTE_WINTER"
        in rule_ids
    )

    assert (
        "SHAKTI_INTERNAL_SLA"
        in rule_ids
    )


def test_bs4_delhi_winter():

    eligible, rules = evaluate(
        vehicle={
            "bs_stage": "BS4",
        },
        trip_context={
            "destination_region": "Delhi_NCR",
        },
        today="2026-01-15",
    )

    assert eligible is False

    assert (
        "BS4_DELHI_NCR_SEASONAL"
        in rules
    )


def test_bs4_delhi_summer():

    eligible, _ = evaluate(
        vehicle={
            "bs_stage": "BS4",
        },
        trip_context={
            "destination_region": "Delhi_NCR",
        },
        today="2026-05-15",
    )

    assert eligible is True


def test_hill_route_requires_heater():

    eligible, rules = evaluate(
        vehicle={
            "engine_heater": "No",
        },
        trip_context={
            "hill_route": True,
        },
        today="2026-01-15",
    )

    assert eligible is False

    assert (
        "HILL_ROUTE_WINTER"
        in rules
    )


def test_hill_route_with_heater_and_old_brakes():

    eligible, _ = evaluate(
        vehicle={
            "engine_heater": "Yes",
        },
        trip_context={
            "hill_route": True,
            "last_brake_work_date": "2025-12-01",
        },
        today="2026-01-15",
    )

    assert eligible is True


def test_hill_route_recent_brakes_rejected():

    eligible, _ = evaluate(
        vehicle={
            "engine_heater": "Yes",
        },
        trip_context={
            "hill_route": True,
            "last_brake_work_date": "2026-01-01",
        },
        today="2026-01-15",
    )

    assert eligible is False


def test_shakti_sla():

    assert (
        get_client_sla(
            "Shakti Cement"
        )
        == 36
    )


def test_orion_old_vehicle_rejected():

    eligible, rules = evaluate(
        vehicle={
            "model_year": 2019,
        },
        trip_context={
            "client": "Orion Pharma",
        },
    )

    assert eligible is False

    assert (
        "ORION_MIN_MODEL_YEAR"
        in rules
    )


def test_orion_new_vehicle_allowed():

    eligible, _ = evaluate(
        vehicle={
            "model_year": 2020,
        },
        trip_context={
            "client": "Orion Pharma",
        },
    )

    assert eligible is True


def test_service_overdue_grounded():

    eligible, rules = evaluate(
        vehicle={},
        trip_context={
            "service_due_date": "2025-12-01",
        },
        today="2026-01-15",
    )

    assert eligible is False

    assert (
        "SERVICE_OVERDUE_30_DAYS"
        in rules
    )


def test_driver_under_six_months():

    eligible, rules = evaluate(
        driver={
            "tenure_months": 5.5,
        },
        trip_context={
            "night_run": True,
            "solo": True,
        },
    )

    assert eligible is False

    assert (
        "NEW_DRIVER_NIGHT_RUN"
        in rules
    )


def test_driver_at_six_months():

    eligible, _ = evaluate(
        driver={
            "tenure_months": 6,
        },
        trip_context={
            "night_run": True,
            "solo": True,
        },
    )

    assert eligible is True


def test_monsoon_east_lucknow():

    multiplier = get_eta_multiplier(
        {
            "route_east_of_lucknow": True,
        },
        date(2026, 8, 15),
    )

    assert multiplier == 1.20


def test_monsoon_other_route():

    multiplier = get_eta_multiplier(
        {
            "route_east_of_lucknow": False,
        },
        date(2026, 8, 15),
    )

    assert multiplier == 1.0


def test_origin_hub_replacement():

    result = replacement_hub(
        {
            "breakdown_distance_from_origin_km": 40,
            "origin_hub": "Kanpur",
        }
    )

    assert result == "Kanpur"


def test_far_breakdown():

    result = replacement_hub(
        {
            "breakdown_distance_from_origin_km": 75,
            "origin_hub": "Kanpur",
        }
    )

    assert result is None


def test_jugaad_active():

    result = get_jugaad_restriction(
        (
            "AC compressor smoke aa raha tha, "
            "band kiya jugaad se, "
            "permanent fix baaki hai."
        ),
        "2026-03-18",
        "2026-03-20",
    )

    assert result is not None
    assert result["active"] is True
    assert result["days_remaining"] == 5
    assert (
        result["restrict_to_home_region"]
        is True
    )


def test_jugaad_expired():

    result = get_jugaad_restriction(
        (
            "band kiya jugaad se, "
            "permanent fix baaki hai."
        ),
        "2026-03-01",
        "2026-03-10",
    )

    assert result is None