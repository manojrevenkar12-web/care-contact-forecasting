# Skills for this codebase

## Add a forecaster
1. Write it in `src/ccf/models/forecasters.py` with the signature `(store, origin, horizon, y) -> [series, horizon]`,
   reading only days before `origin`, and add it to `MODELS` and `all_forecasts`.
2. Add it to `test_forecasts_do_not_look_ahead`.
3. `make eval`; it is scored on WAPE, peak-period WAPE, bias, interval coverage and the staffing it buys.

## Add a driver
A new demand driver (a marketing push, a carrier change) is a column in a mart (`src/ccf/etl/sql/02_marts.sql`)
with a data test, then a block of lag features in `driver_design`. Known-in-advance drivers need a plan column.

## Explain a forecast to operations
`decompose` in `src/ccf/analysis/insights.py` splits each forecast day into reasons and into orders of the last
week against older orders (the returns wave). The dashboard shows the latest origin.

## Change a setting
Only in `config/*.toml`, with the development numbers before and after in the commit message.
