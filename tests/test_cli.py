from datetime import datetime, timezone

from flask import Flask

from flexmeasures_price_importer import cli
from flexmeasures_price_importer.api import price_importer_blueprint
from flexmeasures_price_importer.models import PricePoint


def test_import_prices_commits_both_sensor_writes(monkeypatch) -> None:
    stores = []

    class FakeStore:
        def __init__(self) -> None:
            self.saved_sensors = []
            self.commits = 0
            stores.append(self)

        def find_price_sensors(self, provider, resolution):
            return "consumption", "production"

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
    assert stores[0].saved_sensors == ["consumption", "production"]
    assert stores[0].commits == 1
    assert "Imported 1 hourly prices" in result.output