"""Data structures used by the price importer."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PricePoint:
    timestamp: datetime
    price: float
    unit: str | None = None
    energy_tax: float = 0.0

    @property
    def production_price(self) -> float:
        """Return the same price without energy tax."""
        return round(self.price - self.energy_tax, 6)
