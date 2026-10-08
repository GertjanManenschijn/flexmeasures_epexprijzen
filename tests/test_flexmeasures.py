from datetime import datetime, timezone
from types import SimpleNamespace

from flexmeasures_price_importer.flexmeasures import NativeFlexMeasuresStore
from flexmeasures_price_importer.models import PricePoint


class FakeBelief:
    def __init__(self, **kwargs):
        self.data = kwargs


class FakeDataFrame:
    def __init__(self, beliefs):
        self.beliefs = beliefs


def test_existing_price_asset_gets_name_and_location_update():
    asset_type = object()
    asset = SimpleNamespace(
        name="Nederland",
        latitude=None,
        longitude=None,
        generic_asset_type=asset_type,
    )

    class FakeField:
        def in_(self, values):
            return values

        def __eq__(self, other):
            return other

    class FakeAssetTypeQuery:
        def filter_by(self, **kwargs):
            return self

        def one_or_none(self):
            return asset_type

    class FakeAssetQuery:
        def filter_by(self, **kwargs):
            return SimpleNamespace(one_or_none=lambda: None)

        def filter(self, *conditions):
            return SimpleNamespace(one_or_none=lambda: asset)

    class FakeAsset:
        name = FakeField()
        generic_asset_type = FakeField()
        query = FakeAssetQuery()

    commits = []
    store = object.__new__(NativeFlexMeasuresStore)
    store.GenericAssetType = SimpleNamespace(query=FakeAssetTypeQuery())
    store.GenericAsset = FakeAsset
    store.db = SimpleNamespace(session=SimpleNamespace(commit=lambda: commits.append(True)))

    result = store.get_or_create_public_price_asset(
        "Transmission zone Nederland",
        legacy_names=("Nederland",),
        latitude=52.1326,
        longitude=5.2913,
    )

    assert result is asset
    assert asset.name == "Transmission zone Nederland"
    assert (asset.latitude, asset.longitude) == (52.1326, 5.2913)
    assert commits == [True]


def test_filter_new_prices_keeps_tomorrow_when_today_exists():
    today = PricePoint(datetime(2026, 1, 1, tzinfo=timezone.utc), 0.30)
    tomorrow = PricePoint(datetime(2026, 1, 2, tzinfo=timezone.utc), 0.31)

    class FakeField:
        def in_(self, values):
            return values

        def __eq__(self, other):
            return other

    class FakeQuery:
        def filter(self, *conditions):
            return self

        def all(self):
            return [SimpleNamespace(event_start=today.timestamp)]

    store = object.__new__(NativeFlexMeasuresStore)
    store.TimedBelief = SimpleNamespace(
        sensor=FakeField(),
        event_start=FakeField(),
        query=FakeQuery(),
    )

    result = store.filter_new_prices(object(), [today, tomorrow])

    assert result == [tomorrow]


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