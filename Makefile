PY ?= python3
export PYTHONPATH := src

.PHONY: data test eval heldout report web check

data:      ## the world and the warehouse: raw tables, SQL marts, data tests (~10 s)
	$(PY) scripts/build_world.py && $(PY) -c "from ccf.etl.run import run; print(run())"
test:      ## erlang, calendar, no look-ahead, driver vs naive, data tests, isolation (~30 s)
	$(PY) -m pytest -q
eval:      ## the backtest on the development origins -> reports/dev.json (~12 min)
	$(PY) scripts/evaluate.py
heldout:   ## once: the held-out origins -> reports/heldout.json
	$(PY) scripts/heldout.py
report:    ## README tables and the dashboard's data
	$(PY) scripts/report.py
web:
	cd web && npm ci && npm test && npm run build
check: data test
