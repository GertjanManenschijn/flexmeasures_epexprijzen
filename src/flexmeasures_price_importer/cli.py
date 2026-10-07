"""Command-line interface for EPEX to FlexMeasures imports."""

from datetime import datetime, timedelta

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


@price_importer_blueprint.cli.command("register-price-sensors")
@with_appcontext
@click.argument("provider")
@click.argument("interval", type=click.Choice(["hourly", "quarterly"]))
def register_sensors(
    provider: str,
    interval: str,
) -> None:
    """Create provider-specific price sensors under the public Netherlands zone."""
    provider_label = _provider_label(provider)
    consumption_name = f"{provider_label} consumption price"
    production_name = f"{provider_label} production price"
    store = NativeFlexMeasuresStore()
    try:
        asset = store.get_or_create_public_price_asset("Nederland")
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    for name in (consumption_name, production_name):
        sensor = store.get_or_create_price_sensor(
            asset.id,
            name,
            _resolution(interval)[1],
            "Europe/Amsterdam",
        )
        click.echo(f"{name}: {sensor.id}")


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
        consumption_sensor, production_sensor = store.find_price_sensors(
            provider, _resolution(interval)[1]
        )
        store.ensure_prices_are_new(consumption_sensor, points)
        store.ensure_prices_are_new(production_sensor, points)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    belief_time = datetime.fromisoformat(prior) if prior else None
    store.save_prices(consumption_sensor, points, lambda point: point.price, belief_time)
    store.save_prices(production_sensor, points, lambda point: point.production_price, belief_time)
    click.echo(f"Imported {len(points)} {interval} prices for consumption and production.")



