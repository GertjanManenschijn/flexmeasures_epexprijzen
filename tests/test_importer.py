from flexmeasures_price_importer.importer import PriceImportError, parse_csv, parse_epex_response


def test_parse_csv_returns_timezone_aware_points():
    points = parse_csv(
        "timestamp,price,unit\n"
        "2026-01-01T00:00:00+01:00,125.5,EUR/MWh\n"
    )

    assert points[0].price == 125.5
    assert points[0].unit == "EUR/MWh"
    assert points[0].timestamp.isoformat() == "2026-01-01T00:00:00+01:00"


def test_parse_csv_rejects_naive_timestamps():
    try:
        parse_csv("timestamp,price\n2026-01-01T00:00:00,10\n")
    except PriceImportError as error:
        assert "timezone" in str(error)
    else:
        raise AssertionError("Expected a timezone validation error")


def test_parse_epex_response_removes_energy_tax_for_production():
    points = parse_epex_response(
        {
            "today": [{"t": "2026-01-01T00:00:00Z", "price": 0.30}],
            "tomorrow": [],
            "energy_tax": 0.11,
        }
    )

    assert points[0].price == 0.30
    assert points[0].production_price == 0.19
