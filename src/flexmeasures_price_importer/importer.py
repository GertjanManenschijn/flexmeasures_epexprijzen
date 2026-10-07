"""Parsing and validation of imported price data."""

import csv
import io
import math
from datetime import datetime
from typing import Any

import requests

from .models import PricePoint


class PriceImportError(ValueError):
    """Raised when price data cannot be parsed or validated."""


def epex_url(provider: str, interval: str) -> str:
    if interval not in {"hourly", "quarterly"}:
        raise PriceImportError("interval must be hourly or quarterly")
    return f"https://epexprijzen.nl/api/v1/prices/{provider}/{interval}"


def fetch_epex_prices(
    provider: str,
    interval: str,
    session: requests.Session | None = None,
) -> list[PricePoint]:
    """Fetch today's and tomorrow's prices from the EPEX API."""
    response = (session or requests).get(epex_url(provider, interval), timeout=30)
    response.raise_for_status()
    return parse_epex_response(response.json())


def parse_epex_response(payload: dict[str, Any]) -> list[PricePoint]:
    """Parse the EPEX response into chronologically ordered price points."""
    try:
        energy_tax = float(payload.get("energy_tax", 0.0))
        rows = [*payload.get("today", []), *payload.get("tomorrow", [])]
    except (TypeError, ValueError) as error:
        raise PriceImportError("EPEX response has invalid tax data") from error

    points: list[PricePoint] = []
    for row in rows:
        try:
            timestamp = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
            price = float(row["price"])
        except (KeyError, TypeError, ValueError) as error:
            raise PriceImportError("EPEX response contains an invalid price row") from error
        if timestamp.tzinfo is None or not math.isfinite(price):
            raise PriceImportError("EPEX price rows must have aware timestamps and finite prices")
        points.append(PricePoint(timestamp, price, "EUR/kWh", energy_tax))

    if not points:
        raise PriceImportError("EPEX response contains no price rows")
    return sorted(points, key=lambda point: point.timestamp)


def parse_csv(contents: str) -> list[PricePoint]:
    """Parse the legacy CSV format used by the initial scaffold."""
    reader = csv.DictReader(io.StringIO(contents))
    required_columns = {"timestamp", "price"}
    if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
        raise PriceImportError("CSV must contain timestamp and price columns")

    points: list[PricePoint] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            timestamp = datetime.fromisoformat(row["timestamp"])
            price = float(row["price"])
        except (TypeError, ValueError) as error:
            raise PriceImportError(f"Invalid data on CSV row {row_number}") from error

        if timestamp.tzinfo is None:
            raise PriceImportError(f"Timestamp on CSV row {row_number} must include a timezone")
        if price != price or price in (float("inf"), float("-inf")):
            raise PriceImportError(f"Price on CSV row {row_number} must be finite")

        points.append(PricePoint(timestamp=timestamp, price=price, unit=row.get("unit") or None))

    if not points:
        raise PriceImportError("CSV contains no price rows")
    return points
