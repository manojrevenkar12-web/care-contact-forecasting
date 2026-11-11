"""From a daily forecast to agents per half hour, and what those agents achieve against the volume that came.

The intraday shape is the average share of the day in each half hour over the weeks before the origin, for
weekdays and weekends separately. Phone and chat are staffed with Erlang C; chat agents handle several chats.
"""

from __future__ import annotations

import numpy as np

from ccf.config import forecast
from ccf.data import Store
from ccf.staffing.erlang import offered_load, required_agents, service_level

CHANNELS = ("phone", "chat")


def intraday_shape(store: Store, origin: int) -> np.ndarray:
    """[market, channel, weekend(0/1), slot] shares from the weeks before the origin."""
    weeks = forecast()["staffing"]["intraday_weeks"]
    lo = origin - 7 * weeks
    days = np.arange(lo, origin)
    weekend = store.cal["weekday"][0, days] >= 5
    out = np.zeros((len(store.markets), 2, 2, store.intraday.shape[-1]))
    for k, sel in ((0, ~weekend), (1, weekend)):
        tot = store.intraday[:, :, days[sel], :].sum(axis=2)
        out[:, :, k, :] = tot / np.maximum(tot.sum(axis=-1, keepdims=True), 1)
    return out


def daily_by_market_channel(store: Store, f: np.ndarray) -> np.ndarray:
    """[market, channel(phone, chat), day] from a [series, day] forecast."""
    out = np.zeros((len(store.markets), 2, f.shape[1]))
    for s, name in enumerate(store.series):
        m, c, _ = name.split("|")
        if c in CHANNELS:
            out[store.markets.index(m), CHANNELS.index(c)] += f[s]
    return out


def evaluate(store: Store, origin: int, forecasts: dict[str, np.ndarray]) -> dict[str, dict]:
    cfg = forecast()["staffing"]
    h0, h1 = cfg["horizon_days"]
    days = np.arange(origin + h0 - 1, origin + h1)  # horizon days h0..h1, 1-based
    rel = days - origin
    shape = intraday_shape(store, origin)
    weekend = (store.cal["weekday"][0, days] >= 5).astype(int)
    actual = store.intraday[:, :, days, :]  # [market, channel, day, slot]
    horizon = next(iter(forecasts.values())).shape[1]
    # perfect daily totals still go through the usual intraday shape: the part of misplaced hours no daily forecast can fix
    variants = {**forecasts, "perfect daily totals": store.y[:, origin : origin + horizon], "perfect forecast": None}
    out = {}
    for name, f in variants.items():
        totals = {"agent_hours": 0.0, "intervals": 0, "intervals_met": 0, "contacts": 0.0, "late": 0.0, "hours_over": 0.0, "hours_short": 0.0}
        for ci, ch in enumerate(CHANNELS):
            p = cfg[ch]
            conc = p.get("concurrency", 1)
            if f is None:
                vol_plan = actual[:, ci]
            else:
                daily = daily_by_market_channel(store, f[:, rel])[:, ci]  # [market, day]
                vol_plan = daily[:, :, None] * shape[:, ci, weekend, :]
            n = required_agents(offered_load(vol_plan, p["aht"], cfg["interval_seconds"], conc), p["aht"] / conc, p["answer_within"], p["service_level"])
            act = actual[:, ci]
            needed = required_agents(offered_load(act, p["aht"], cfg["interval_seconds"], conc), p["aht"] / conc, p["answer_within"], p["service_level"])
            hours = cfg["interval_seconds"] / 3600
            totals["hours_over"] += float(np.maximum(n - needed, 0).sum() * hours)
            totals["hours_short"] += float(np.maximum(needed - n, 0).sum() * hours)
            sl = service_level(n, offered_load(act, p["aht"], cfg["interval_seconds"], conc), p["aht"] / conc, p["answer_within"])
            totals["agent_hours"] += n.sum() * cfg["interval_seconds"] / 3600
            totals["intervals"] += n.size
            totals["intervals_met"] += int((sl >= p["service_level"] - 1e-9).sum())
            totals["contacts"] += act.sum()
            totals["late"] += float((act * (1 - sl)).sum())
        out[name] = totals
    return out
