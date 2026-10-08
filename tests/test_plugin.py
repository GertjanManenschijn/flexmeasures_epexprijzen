from flask import Blueprint

import flexmeasures_price_importer


def test_package_exposes_one_blueprint() -> None:
    blueprints = [
        getattr(flexmeasures_price_importer, attribute)
        for attribute in dir(flexmeasures_price_importer)
        if isinstance(getattr(flexmeasures_price_importer, attribute), Blueprint)
    ]

    assert blueprints == [flexmeasures_price_importer.blueprint]
    assert flexmeasures_price_importer.create_blueprint() is blueprints[0]