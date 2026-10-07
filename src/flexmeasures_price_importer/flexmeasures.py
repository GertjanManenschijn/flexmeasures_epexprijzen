"""Native FlexMeasures persistence for imported EPEX prices."""

from datetime import datetime, timedelta
from typing import Any

from .models import PricePoint


class NativeFlexMeasuresStore:
    """Persist sensors and beliefs through the hosting FlexMeasures app."""

    def __init__(self) -> None:
        from flexmeasures.data import db
        from flexmeasures.data.models.generic_assets import GenericAsset, GenericAssetType
        from flexmeasures.data.models.time_series import Sensor, TimedBelief
        from flexmeasures.data.services.data_sources import get_or_create_source
        from flexmeasures.data.utils import save_to_db
        from flexmeasures.utils.time_utils import server_now
        from timely_beliefs import BeliefsDataFrame

        self.db = db
        self.GenericAsset = GenericAsset
        self.GenericAssetType = GenericAssetType
        self.Sensor = Sensor
        self.TimedBelief = TimedBelief
        self.get_or_create_source = get_or_create_source
        self.save_to_db = save_to_db
        self.server_now = server_now
        self.BeliefsDataFrame = BeliefsDataFrame

    def _asset(self, asset_id: int) -> Any:
        asset = self.db.session.get(self.GenericAsset, asset_id)
        if asset is None:
            raise ValueError(f"FlexMeasures asset {asset_id} does not exist")
        return asset

    def get_or_create_public_price_asset(self, name: str) -> Any:
        """Find or create an account-less public asset of the standard zone type."""
        asset_type = self.GenericAssetType.query.filter_by(name="transmission zone").one_or_none()
        if asset_type is None:
            raise ValueError(
                "FlexMeasures asset type 'transmission zone' is not available"
            )

        asset = self.GenericAsset.query.filter_by(
            name=name,
            generic_asset_type=asset_type,
        ).one_or_none()
        if asset is None:
            asset = self.GenericAsset(
                name=name,
                generic_asset_type=asset_type,
            )
            self.db.session.add(asset)
            self.db.session.commit()
        return asset

    def get_or_create_price_sensor(
        self,
        asset_id: int,
        name: str,
        resolution: timedelta,
        timezone: str,
    ) -> Any:
        asset = self._asset(asset_id)
        sensor = self.Sensor.query.filter_by(name=name, generic_asset_id=asset_id).one_or_none()
        if sensor is None:
            sensor = self.Sensor(
                name=name,
                unit="EUR/kWh",
                event_resolution=resolution,
                timezone=timezone,
                generic_asset=asset,
                attributes={"floor_datetimes_to_resolution": True},
            )
            self.db.session.add(sensor)
            self.db.session.commit()
        return sensor

    def find_price_sensors(self, provider: str, resolution: timedelta) -> tuple[Any, Any]:
        """Find the unique provider price sensors for a transmission zone."""
        provider_label = provider.replace("-", " ").title()
        names = (
            f"{provider_label} consumption price",
            f"{provider_label} production price",
        )
        candidates = self.Sensor.query.filter(self.Sensor.name.in_(names)).all()
        sensors = [
            sensor
            for sensor in candidates
            if sensor.event_resolution == resolution
            and sensor.generic_asset.generic_asset_type.name == "transmission zone"
        ]
        matches = {name: [sensor for sensor in sensors if sensor.name == name] for name in names}
        missing = [name for name, found in matches.items() if not found]
        ambiguous = [name for name, found in matches.items() if len(found) > 1]
        if missing or ambiguous:
            details = []
            if missing:
                details.append("not found: " + ", ".join(missing))
            if ambiguous:
                details.append("ambiguous across transmission zones: " + ", ".join(ambiguous))
            raise ValueError(
                "Price sensor lookup failed (" + "; ".join(details) + ")"
            )
        consumption_sensor = matches[names[0]][0]
        production_sensor = matches[names[1]][0]
        if consumption_sensor.generic_asset_id != production_sensor.generic_asset_id:
            raise ValueError("Consumption and production price sensors belong to different assets")
        return consumption_sensor, production_sensor

    def ensure_prices_are_new(self, sensor: Any, points: list[PricePoint]) -> None:
        """Reject an import when any event for this sensor already exists."""
        event_starts = [point.timestamp for point in points]
        existing = self.TimedBelief.query.filter(
            self.TimedBelief.sensor == sensor,
            self.TimedBelief.event_start.in_(event_starts),
        ).count()
        if existing:
            raise ValueError(
                f"{existing} price event(s) already exist for sensor {sensor.id}; import aborted"
            )

    def save_prices(
        self,
        sensor: Any,
        points: list[PricePoint],
        value_getter: Any,
        prior: datetime | None = None,
    ) -> str:
        source = self.get_or_create_source(
            source="EPEX Prices",
            source_type="market",
            flush=False,
        )
        belief_time = prior or self.server_now()
        beliefs = [
            self.TimedBelief(
                event_start=point.timestamp,
                belief_time=belief_time,
                event_value=value_getter(point),
                sensor=sensor,
                source=source,
            )
            for point in points
        ]
        return self.save_to_db(self.BeliefsDataFrame(beliefs))
