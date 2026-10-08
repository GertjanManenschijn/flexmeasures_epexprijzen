# FlexMeasures price importer

A CLI plugin for importing electricity price data from epexprijzen.nl into FlexMeasures.

## Current scope

The project provides:

- a `register-price-sensors` command for creating two EUR/kWh sensors;
- an `import-prices` command for fetching hourly or quarter-hourly EPEX prices;
- posting to a consumption sensor with the price including energy tax; and
- posting to a production sensor with `price - energy_tax`.

The provider charge is retained in the production price because it is an energy-price component, not a tax. The plugin runs inside FlexMeasures and writes directly through FlexMeasures models and `save_to_db`; no FlexMeasures REST credentials are needed.

## Setup

```powershell
python -m pip install -e ".[dev]"
```

Create a public `transmission zone` asset and register both provider-specific sensors:

```powershell
flexmeasures epex-prices register-price-sensors anwb-energie hourly
```

All providers are registered under the public `Transmission zone Nederland` asset, located at the approximate geographic centre of the Netherlands (`52.1326, 5.2913`).

Import today and tomorrow from EPEX through FlexMeasures:

```powershell
flexmeasures epex-prices import-prices anwb-energie hourly
```

Use `--prior` optionally to record the publication time of day-ahead prices. The command creates missing provider sensors automatically and aborts if any requested event has already been imported. The commands require a running FlexMeasures app context and are exposed only through FlexMeasures.

## FlexMeasures plugin loading

The package still exposes a Blueprint and can be loaded by FlexMeasures through `FLEXMEASURES_PLUGINS`:

```text
FLEXMEASURES_PLUGINS=flexmeasures_price_importer
```
