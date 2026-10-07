from datetime import datetime, timezone

from flexmeasures_price_importer.flexmeasures import NativeFlexMeasuresStore
from flexmeasures_price_importer.models import PricePoint


class FakeBelief:
    def __init__(self, **kwargs):
        self.data = kwargs


class FakeDataFrame:
    def __init__(self, beliefs):
        self.beliefs = beliefs


def test_save_prices_builds_native_timed_beliefs():
    store = object.__new__(NativeFlexMeasuresStore)
    store.get_or_create_source = lambda **kwargs: "epex-source"
    store.server_now = lambda: datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    store.TimedBelief = FakeBelief
    store.BeliefsDataFrame = FakeDataFrame
    store.save_to_db = lambda data: f"saved {len(data.beliefs)}"
    sensor = object()
    points = [
        PricePoint(datetime(2026, 1, 1, tzinfo=timezone.utc), 0.30, "EUR/kWh", 0.11)
    ]

    result = store.save_prices(sensor, points, lambda point: point.production_price)

    assert result == "saved 1"
    assert store.BeliefsDataFrame