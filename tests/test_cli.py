from datetime import datetime, timezone
from types import SimpleNamespace

from flask import Flask

from flexmeasures_price_importer import cli
from flexmeasures_price_importer.api import price_importer_blueprint
from flexmeasures_price_importer.models import PricePoint


def test_register_sensors_uses_named_transmission_zone(monkeypatch) -> None:
    asset_requests = []

    class FakeStore:
        def get_or_create_public_price_asset(self, name, legacy_names=()):
            asset_requests.append((name, legacy_names))
            return SimpleNamespace(id=7)

        def get_or_create_price_sensor(self, asset_id, name, resolution, timezone):
            return SimpleNamespace(id=len(name), name=name)

    monkeypatch.setattr(cli, "NativeFlexMeasuresStore", FakeStore)
    app = Flask(__name__)
    app.register_blueprint(price_importer_blueprint)

    result = app.test_cli_runner().invoke(
        args=["epex-prices", "register-price-sensors", "anwb-energie", "hourly"]
    )

    assert result.exit_code == 0
    assert asset_requests == [
        ("Transmission zone Nederland", ("Nederland",)),
    ]


def test_import_prices_commits_both_sensor_writes(monkeypatch) -> None:
    stores = []

    class FakeStore:
        def __init__(self) -> None:
            self.created_sensors = []
            self.saved_sensors = []
            self.commits = 0
            stores.append(self)

        def get_or_create_public_price_asset(self, name, legacy_names=()):
            return SimpleNamespace(id=7)

        def get_or_create_price_sensor(self, asset_id, name, resolution, timezone):
            sensor = SimpleNamespace(id=len(name), name=name)
            self.created_sensors.append(sensor)
            return sensor

        def ensure_prices_are_new(self, sensor, points) -> None:
            pass

        def save_prices(self, sensor, points, value_getter, prior) -> None:
            self.saved_sensors.append(sensor)

        def commit(self) -> None:
            self.commits += 1

    points = [PricePoint(datetime(2026, 1, 1, tzinfo=timezone.utc), 0.30)]
    monkeypatch.setattr(cli, "fetch_epex_prices", lambda provider, interval: points)
    monkeypatch.setattr(cli, "NativeFlexMeasuresStore", FakeStore)
    app = Flask(__name__)
    app.register_blueprint(price_importer_blueprint)

    result = app.test_cli_runner().invoke(
        args=["epex-prices", "import-prices", "anwb-energie", "hourly"]
    )

    assert result.exit_code == 0
    assert [sensor.name for sensor in stores[0].created_sensors] == [
        "Anwb Energie consumption price",
        "Anwb Energie production price",
    ]
    assert stores[0].saved_sensors == stores[0].created_sensors
    assert stores[0].commits == 1
    assert "Imported 1 hourly prices" in result.output