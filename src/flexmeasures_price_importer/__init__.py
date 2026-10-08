"""FlexMeasures plugin for importing electricity price data."""

from flask import Blueprint

from .api import price_importer_blueprint as blueprint

# Importing the CLI module registers its Click commands on the Blueprint.
from . import cli as _cli  # noqa: F401

__version__ = "0.1.1"


def create_blueprint() -> Blueprint:
    """Return the blueprint that FlexMeasures should register."""
    return blueprint
