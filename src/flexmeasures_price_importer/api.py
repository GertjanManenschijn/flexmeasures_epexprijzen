"""FlexMeasures Blueprint used to register the plugin CLI."""

from flask import Blueprint

price_importer_blueprint = Blueprint(
    "price_importer",
    __name__,
    url_prefix="/price-importer",
    cli_group="epex-prices",
)
