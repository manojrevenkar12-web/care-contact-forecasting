"""Forecasts on the generated world: no look-ahead, the driver model beats the naive one, and the data tests hold."""

import copy

import numpy as np

from ccf.models.forecasters import driver_forecast, gbm, seasonal_naive


def test_forecasts_do_not_look_ahead(store):
    o, h = store.index("2025-03-03"), 28
    future_changed = copy.copy(store)
    future_changed.y = store.y.copy()
    future_changed.y[:, o:] *= 3  # what happens after the origin must not change the forecast
    for fn in (lambda s: driver_forecast(s, o, h)[0], lambda s: seasonal_naive(s, o, h), lambda s: gbm(s, o, h, s.y)):
        assert np.allclose(fn(store), fn(future_changed))


def test_the_driver_model_beats_last_week_repeated(store):
    o, h = store.index("2025-05-05"), 42
    actual = store.y[:, o : o + h]
    wape = lambda f: np.abs(f - actual).sum() / actual.sum()  # noqa: E731
    assert wape(driver_forecast(store, o, h)[0]) < 0.8 * wape(seasonal_naive(store, o, h))


def test_the_warehouse_passes_its_data_tests(store):
    from ccf.etl.run import connect, tests

    assert all(n == 0 for n in tests(connect()).values())
