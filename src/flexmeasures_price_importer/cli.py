"""Command-line interface for EPEX to FlexMeasures imports."""

from datetime import datetime, timedelta
from typing import Any

import click
from flask.cli import with_appcontext

from .flexmeasures import NativeFlexMeasuresStore
from .importer import fetch_epex_prices
from .api import price_importer_blueprint


def _resolution(interval: str) -> tuple[str, timedelta]:
    if interval == "hourly":
        return "PT1H", timedelta(hours=1)
    return "PT15M", timedelta(minutes=15)


def _provider_label(provider: str) -> str:
    return provider.replace("-", " ").title()


def _get_or_create_price_sensors(
    store: NativeFlexMeasuresStore,
    provider: str,
    interval: str,
) -> tuple[Any, Any]:
    provider_label = _provider_label(provider)
    asset = store.get_or_create_public_price_asset(
        "Transmission zone Nederland",
        legacy_names=("Nederland",),
        latitude=52.1326,
        longitude=5.2913,
    )
    sensors = tuple(
        store.get_or_create_price_sensor(
            asset.id,
            f"{provider_label} {direction} price",
            _resolution(interval)[1],
            "Europe/Amsterdam",
        )
        for direction in ("consumption", "production")
    )
    return sensors


@price_importer_blueprint.cli.command("register-price-sensors")
@with_appcontext
@click.argument("provider")
@click.argument("interval", type=click.Choice(["hourly", "quarterly"]))
def register_sensors(
    provider: str,
    interval: str,
) -> None:
    """Create provider-specific price sensors under the public Netherlands zone."""
    store = NativeFlexMeasuresStore()
    try:
        sensors = _get_or_create_price_sensors(store, provider, interval)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    for sensor in sensors:
        click.echo(f"{sensor.name}: {sensor.id}")


@price_importer_blueprint.cli.command("import-prices")
@with_appcontext
@click.argument("provider")
@click.argument("interval", type=click.Choice(["hourly", "quarterly"]))
@click.option("--prior", help="ISO timestamp at which the day-ahead prices became known")
def import_prices(
    provider: str,
    interval: str,
    prior: str | None,
) -> None:
    """Fetch EPEX prices and post them to both price sensors."""
    points = fetch_epex_prices(provider, interval)
    store = NativeFlexMeasuresStore()
    try:
        consumption_sensor, production_sensor = _get_or_create_price_sensors(
            store, provider, interval
        )
        store.ensure_prices_are_new(consumption_sensor, points)
        store.ensure_prices_are_new(production_sensor, points)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    belief_time = datetime.fromisoformat(prior) if prior else None
    store.save_prices(consumption_sensor, points, lambda point: point.price, belief_time)
    store.save_prices(production_sensor, points, lambda point: point.production_price, belief_time)
    store.commit()
    click.echo(f"Imported {len(points)} {interval} prices for consumption and production.")



