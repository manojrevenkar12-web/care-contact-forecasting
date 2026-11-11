# AGENTS.md

How to work in this repository, for people and coding agents.

## Fast feedback
- `make data` builds the world and the warehouse and runs the SQL data tests (~10 s).
- `make test` runs everything else in about 30 s: Erlang C against the textbook case, the calendar, forecasts that
  do not change when the future changes (no look-ahead), the driver model against the naive one, isolation.
- `make eval` is the full development backtest (~12 min).

## Invariants
1. **Forecasters never read the truth.** `data/truth/` is read only by `ccf.evals`; `tests/test_isolation.py` fails
   otherwise. A forecaster reads contacts before its origin, the order plan and the calendar.
2. **No look-ahead.** A forecast made at an origin is the same whatever happens after it; there is a test.
3. **Scored where it is used.** Error is measured at market x channel per day, the grain capacity planning staffs,
   and every model is also scored by the staffing it would have bought.
4. **SQL owns the data model.** Staging, marts and data tests live in `src/ccf/etl/sql`; Python reads the marts.
5. **Settings live in config.** `config/world.toml` for the world, `config/forecast.toml` for models, staffing, gate.
6. **Reports are generated.** `reports/*.json`, the README tables and the dashboard data come from the scripts.

## The held-out rule
The held-out origins (Q4 2025, Cyber Week included) and the world are pinned in `config/heldout.lock` and run once;
`make heldout` refuses to overwrite `reports/heldout.json`. The chosen model and every setting are fixed from the
development origins. What was seen of the held-out period is in `docs/heldout-exposure.md`.
