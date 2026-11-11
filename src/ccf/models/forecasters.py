"""The forecasters. Each takes the store, an origin (the first day to forecast) and a horizon, may read only days
before the origin (and the order plan and calendar for any day), and returns [series, horizon] contacts.

- seasonal naive: the last week, repeated;
- ETS: Holt-Winters per series on log volumes, weekly season, damped trend;
- GBM: one LightGBM model for all series, on calendar and order-driver features;
- driver: contacts explained by lagged orders per market and reason, with weekday and holiday factors, then split
  by the recent channel mix. Every number it gives can be traced to the orders behind it;
- ensemble: the mean of GBM and the driver model.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
from scipy.optimize import nnls

from ccf.config import forecast
from ccf.data import Store


@dataclass
class DriverFit:
    """One market x reason: the coefficients and calendar factors, kept for explanations."""

    beta: np.ndarray
    names: list[str]
    weekday: np.ndarray
    holiday: float
    after_holiday: float
    fitted: np.ndarray  # in-sample fit over the training window, aligned to `train_days`
    train_days: np.ndarray
    flagged: np.ndarray  # training days marked as incidents


def lag_features_fast(orders: np.ndarray, bins: list[list[int]], upto: int) -> np.ndarray:
    csum = np.concatenate([[0.0], np.cumsum(orders[:upto])])
    t = np.arange(upto)
    out = np.zeros((len(bins), upto))
    for b, (lo, hi) in enumerate(bins):
        z = t - lo
        a = np.maximum(t - hi, 0)
        ok = z >= 0
        out[b, ok] = csum[z[ok] + 1] - csum[a[ok]]
    return out


def _market_reason_index(store: Store) -> dict[tuple[str, str], list[int]]:
    out: dict[tuple[str, str], list[int]] = {}
    for s, name in enumerate(store.series):
        m, _, r = name.split("|")
        out.setdefault((m, r), []).append(s)
    return out


def driver_design(store: Store, market: str, reason: str, origin: int, upto: int) -> tuple[np.ndarray, list[str]]:
    cfg = forecast()["models"]
    mi = store.markets.index(market)
    t = np.arange(upto) / 365.0
    if reason == "account_other":
        return np.vstack([np.ones(upto), t]), ["base", "trend"]
    app = "lounge" if reason == "lounge" else "fashion"
    orders = store.orders_known(app, origin, upto)[mi]
    x = lag_features_fast(orders, cfg["lag_bins"], upto)
    names = [f"{app} orders {lo}-{hi} days before" if lo != hi else f"{app} orders {lo} days before" for lo, hi in cfg["lag_bins"]]
    return np.vstack([x, np.ones(upto)]), names + ["base"]


def fit_driver(store: Store, y: np.ndarray, market: str, reason: str, origin: int, z_flag: float, min_ratio: float = 1.0) -> tuple[DriverFit, np.ndarray]:
    """Fit on the year before the origin; returns the fit and the design for days 0..origin+horizon handled later."""
    cfg = forecast()["models"]["driver"]
    mi = store.markets.index(market)
    lo = max(28, origin - cfg["history_days"])
    days = np.arange(lo, origin)
    x_all, names = driver_design(store, market, reason, origin, origin)
    x = x_all[:, days].T
    w = 0.5 ** ((origin - 1 - days) / cfg["half_life_days"])
    wd = store.cal["weekday"][mi, days].astype(int)
    hol = store.cal["is_holiday"][mi, days].astype(bool)
    aft = store.cal["is_after_holiday"][mi, days].astype(bool)
    target = y[days]
    f_wd, f_hol, f_aft = np.ones(7), 1.0, 1.0
    flagged = np.zeros(len(days), bool)
    for it in range(4):
        f = f_wd[wd] * np.where(hol, f_hol, 1.0) * np.where(aft, f_aft, 1.0)
        ww = w * ~flagged
        beta, _ = nnls(x * np.sqrt(ww)[:, None], (target / f) * np.sqrt(ww))
        base = x @ beta
        ratio = target / np.maximum(base, 1e-9)
        normal = ~hol & ~aft & ~flagged
        for d in range(7):
            sel = normal & (wd == d)
            if sel.any():
                f_wd[d] = np.average(ratio[sel], weights=w[sel])
        if (hol & ~flagged).any():
            f_hol = np.median(ratio[hol & ~flagged] / f_wd[wd[hol & ~flagged]])
        if (aft & ~flagged).any():
            f_aft = np.median(ratio[aft & ~flagged] / f_wd[wd[aft & ~flagged]])
        fitted = base * f_wd[wd] * np.where(hol, f_hol, 1.0) * np.where(aft, f_aft, 1.0)
        r = np.log((target + 1) / (fitted + 1))
        med = np.median(r)
        mad = 1.4826 * np.median(np.abs(r - med)) + 1e-9
        if it >= 1:
            flagged = ((r - med) / mad > z_flag) & ((target + 1) / (fitted + 1) >= min_ratio)
    return DriverFit(beta, names, f_wd, f_hol, f_aft, fitted, days, flagged), x_all


def driver_forecast(store: Store, origin: int, horizon: int, keep: dict | None = None) -> tuple[np.ndarray, dict]:
    cfg = forecast()["models"]
    upto = origin + horizon
    out = np.zeros((len(store.series), horizon))
    fits = {}
    for (m, r), idx in _market_reason_index(store).items():
        mi = store.markets.index(m)
        total = store.y[idx].sum(axis=0)
        fit, _ = fit_driver(store, total, m, r, origin, cfg["anomaly_z"], cfg["anomaly_min_ratio"])
        x, _ = driver_design(store, m, r, origin, upto)
        fut = np.arange(origin, upto)
        wd = store.cal["weekday"][mi, fut].astype(int)
        f = (
            fit.weekday[wd]
            * np.where(store.cal["is_holiday"][mi, fut] > 0, fit.holiday, 1.0)
            * np.where(store.cal["is_after_holiday"][mi, fut] > 0, fit.after_holiday, 1.0)
        )
        level = x[:, fut].T @ fit.beta * f
        # a lasting change (a bot launch, a new returns policy) shows first as the last weeks running below or above
        # the fit: correct the level by their median ratio, shrunk toward 1
        d = cfg["driver"]
        recent_days = fit.train_days[-d["level_days"] :]
        ok = ~fit.flagged[-d["level_days"] :]
        if ok.sum() >= 7:
            ratio = np.median((total[recent_days][ok] + 1) / (fit.fitted[-d["level_days"] :][ok] + 1))
            level = level * (1 + d["level_weight"] * (ratio - 1))
        recent = slice(origin - cfg["driver"]["channel_share_days"], origin)
        shares = store.y[idx][:, recent].sum(axis=1)
        shares = shares / max(shares.sum(), 1)
        out[idx] = shares[:, None] * level[None, :]
        fits[(m, r)] = (fit, x[:, fut], f)
    return out, fits


def cleaned_history(store: Store, origin: int) -> tuple[np.ndarray, dict]:
    """Contacts before the origin with incident days replaced by the driver fit, per channel by its share."""
    cfg = forecast()["models"]
    y = store.y.copy()
    flags = {}
    for (m, r), idx in _market_reason_index(store).items():
        total = store.y[idx].sum(axis=0)
        fit, _ = fit_driver(store, total, m, r, origin, cfg["anomaly_z"], cfg["anomaly_min_ratio"])
        days = fit.train_days[fit.flagged]
        flags[(m, r)] = days
        if len(days) and cfg["clean_training_data"]:
            share = store.y[idx][:, days] / np.maximum(total[days], 1)
            y[np.ix_(idx, days)] = share * fit.fitted[fit.flagged][None, :]
    return y, flags


def seasonal_naive(store: Store, origin: int, horizon: int, y: np.ndarray | None = None) -> np.ndarray:
    y = store.y if y is None else y
    last = y[:, origin - 7 : origin]
    reps = int(np.ceil(horizon / 7))
    return np.tile(last, reps)[:, :horizon]


def ets(store: Store, origin: int, horizon: int, y: np.ndarray) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    n = forecast()["models"]["ets_history_days"]
    out = np.zeros((len(store.series), horizon))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for s in range(len(store.series)):
            hist = np.log1p(y[s, origin - n : origin])
            model = ExponentialSmoothing(hist, trend="add", damped_trend=True, seasonal="add", seasonal_periods=7, initialization_method="estimated")
            res = model.fit(optimized=True)
            out[s] = np.expm1(res.forecast(horizon))
    return np.maximum(out, 0)


def _gbm_frame(store: Store, origin: int, days: np.ndarray, upto: int) -> tuple[np.ndarray, np.ndarray]:
    cfg = forecast()["models"]
    feats_by_market = {}
    for mi, _m in enumerate(store.markets):
        fa = lag_features_fast(store.orders_known("fashion", origin, upto)[mi], cfg["lag_bins"], upto)
        lo = lag_features_fast(store.orders_known("lounge", origin, upto)[mi], cfg["lag_bins"], upto)
        cal = np.vstack([store.cal[k][mi, :upto] for k in ("weekday", "day_of_year", "is_holiday", "is_after_holiday", "campaign_code", "day_of_campaign")])
        feats_by_market[mi] = np.vstack([np.log1p(fa), np.log1p(lo), cal, np.arange(upto)[None, :]])
    rows, sids = [], []
    reasons = sorted({s.split("|")[2] for s in store.series})
    channels = ["chat", "email", "phone"]
    for s, name in enumerate(store.series):
        m, c, r = name.split("|")
        mi = store.markets.index(m)
        f = feats_by_market[mi][:, days].T
        ids = np.tile([s, mi, channels.index(c), reasons.index(r)], (len(days), 1))
        rows.append(np.hstack([ids, f]))
        sids.append(np.full(len(days), s))
    return np.vstack(rows), np.concatenate(sids)


def gbm(store: Store, origin: int, horizon: int, y: np.ndarray) -> np.ndarray:
    cfg = forecast()
    p = cfg["models"]["gbm"]
    lo = max(28, origin - cfg["backtest"]["history_days"])
    train_days = np.arange(lo, origin)
    x, sid = _gbm_frame(store, origin, train_days, origin + horizon)
    target = np.log1p(y[sid, np.tile(train_days, len(store.series))])
    model = lgb.LGBMRegressor(
        num_leaves=p["num_leaves"],
        n_estimators=p["n_estimators"],
        learning_rate=p["learning_rate"],
        min_child_samples=p["min_child_samples"],
        verbose=-1,
        n_jobs=4,
    )
    model.fit(x, target, categorical_feature=[0, 1, 2, 3])
    fut = np.arange(origin, origin + horizon)
    xf, _ = _gbm_frame(store, origin, fut, origin + horizon)
    return np.maximum(np.expm1(model.predict(xf)).reshape(len(store.series), horizon), 0)


MODELS = ["seasonal_naive", "ets", "gbm", "driver", "ensemble"]


def all_forecasts(store: Store, origin: int, horizon: int) -> tuple[dict[str, np.ndarray], dict, dict]:
    y_clean, flags = cleaned_history(store, origin)
    drv, fits = driver_forecast(store, origin, horizon)
    g = gbm(store, origin, horizon, y_clean)
    out = {
        "seasonal_naive": seasonal_naive(store, origin, horizon),
        "ets": ets(store, origin, horizon, y_clean),
        "gbm": g,
        "driver": drv,
        "ensemble": 0.5 * (g + drv),
    }
    return out, fits, flags
