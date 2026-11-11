"""The simulated retailer: orders, the commercial order plan, and the customer-care contacts they cause.

Contacts follow orders with a lag that depends on the reason (where is my order a few days later, returns and
refunds two to four weeks later), dip on weekends and public holidays and come back the next working day, shift
from email to chat over time, fall where a self-service bot launched, and jump on incident days nobody planned
for. The raw tables are what a forecasting team would have; `data/truth/` is what only the evaluation reads.
"""

from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd

from ccf.config import RAW, TRUTH, world
from ccf.world.calendar import campaigns, holidays

CHANNELS = ["phone", "chat", "email"]
APPS = ["fashion", "lounge"]
MONTH = np.array([1.05, 0.92, 1.0, 1.02, 1.0, 0.95, 0.9, 0.92, 1.0, 1.03, 1.12, 1.18])
CYBER = {-1: 1.5, 0: 2.4, 1: 1.9, 2: 1.7, 3: 2.0}


def kernel(lo: int, hi: int, mode: int) -> np.ndarray:
    k = np.zeros(hi + 1)
    for lag in range(lo, hi + 1):
        if lag <= mode:
            k[lag] = (lag - lo + 1) / (mode - lo + 1)
        else:
            k[lag] = (hi - lag + 1) / (hi - mode + 1)
    return k / k.sum()


def intraday_curve(weekend: bool, n: int) -> np.ndarray:
    x = np.arange(n) + 0.5  # half-hours after opening
    if weekend:
        c = np.exp(-0.5 * ((x - 10) / 6) ** 2)
    else:
        c = np.exp(-0.5 * ((x - 5) / 3) ** 2) + 0.85 * np.exp(-0.5 * ((x - 14) / 4) ** 2) + 0.25
    return c / c.sum()


def build() -> dict:
    cfg = world()
    rng = np.random.default_rng(cfg["seed"])
    days = pd.date_range(cfg["start"], cfg["end"], freq="D")
    n = len(days)
    years = sorted(set(days.year))
    markets = list(cfg["markets"])
    hol = holidays(markets, years)
    camp = campaigns(years)
    o, c = cfg["orders"], cfg["contacts"]

    dow = days.dayofweek.to_numpy()
    t_years = (days - days[0]).days.to_numpy() / 365.0
    camp_factor = np.ones(n)
    return_weight = np.ones(n)
    for _, r in camp.iterrows():
        i = (r["day"] - days[0]).days
        if 0 <= i < n:
            if r["campaign"] == "cyber_week":
                camp_factor[i] = CYBER[r["day_of_campaign"]] * o["cyber_week_peak"] / 2.4
            else:
                camp_factor[i] = 1 + (o["sale_uplift"] - 1) * (1 - r["day_of_campaign"] / 12)
            return_weight[i] = c["returns_after_peaks"]

    orders_rows, plan_rows, contact_rows, intraday_rows = [], [], [], []
    incidents_rows = []
    rates, lags = c["rate"], c["lag"]
    reasons = c["reasons"]
    phone, chat = cfg["channels"]["phone"], cfg["channels"]["chat"]
    bot = cfg["bot"]
    n_int = (cfg["intraday"]["close"] - cfg["intraday"]["open"]) * 2

    for m in markets:
        is_hol = np.isin(days, hol.loc[hol.market == m, "day"].to_numpy())
        level = cfg["markets"][m] * (1 + o["growth_per_year"]) ** t_years
        expected_orders = level * np.array(o["weekday"])[dow] * MONTH[days.month - 1] * camp_factor * np.where(is_hol, o["holiday"], 1.0)
        fashion = rng.poisson(expected_orders * (1 - c["lounge_share_of_orders"]) * rng.lognormal(0, o["noise"], n))
        lounge = rng.poisson(expected_orders * c["lounge_share_of_orders"] * rng.lognormal(0, 0.1, n))
        plan_err = np.where(camp_factor > 1.6, o["cyber_week_plan_error"], o["plan_error"])
        for app, actual in (("fashion", fashion), ("lounge", lounge)):
            share = (1 - c["lounge_share_of_orders"]) if app == "fashion" else c["lounge_share_of_orders"]
            plan = np.round(expected_orders * share * rng.lognormal(0, plan_err, n))
            orders_rows.append(pd.DataFrame({"day": days, "market": m, "app": app, "orders": actual}))
            plan_rows.append(pd.DataFrame({"day": days, "market": m, "app": app, "planned_orders": plan.astype(int)}))

        # expected contacts per reason, before weekday, holiday and incident effects
        exp = {}
        for r in reasons:
            if r == "account_other":
                exp[r] = level * c["account_other_per_1k_orders"] / 1000
                continue
            src = lounge if r == "lounge" else fashion
            weight = return_weight if r == "return_refund" else 1.0
            k = kernel(*lags[r])
            exp[r] = rates[r] * np.convolve(src * weight, k)[:n]
        for r in reasons:
            e = exp[r] * np.array(c["weekday"])[dow]
            missing = np.where(is_hol, e * (1 - c["holiday"]), 0.0)
            e = np.where(is_hol, e * c["holiday"], e)
            nxt = np.roll(missing, 1)
            nxt[0] = 0
            e = e + c["rebound"] * nxt * ~is_hol
            if r == "wismo" and m in bot["markets"]:
                since = (days - pd.Timestamp(bot["launch"])).days.to_numpy()
                ramp = np.clip(since / bot["ramp_days"], 0, 1)
                e = e * (1 + bot["wismo_effect"] * ramp)
            mult = np.ones(n)
            for inc in cfg["incidents"]:
                if inc["markets"] != "all" and m not in inc["markets"]:
                    continue
                if r not in inc["effects"]:
                    continue
                i0 = (pd.Timestamp(inc["start"]) - days[0]).days
                for d in range(inc["days"]):
                    if 0 <= i0 + d < n:
                        mult[i0 + d] = inc["effects"][r]
                        incidents_rows.append({"day": str(days[i0 + d].date()), "market": m, "reason": r, "multiplier": inc["effects"][r]})
            e = e * mult * rng.lognormal(0, c["noise"], n)
            p_phone = phone[r]
            p_chat = np.clip(chat[r] + cfg["channels"]["chat_gain_per_year"] * t_years, 0, 0.95 - p_phone)
            p_email = 1 - p_phone - p_chat
            daily = {}
            for ch, share in (("phone", p_phone), ("chat", p_chat), ("email", p_email)):
                counts = rng.poisson(np.maximum(e * share, 0))
                daily[ch] = counts
                contact_rows.append(pd.DataFrame({"day": days, "market": m, "channel": ch, "reason": r, "contacts": counts}))
            exp[r + "__daily"] = daily
        for ch in ("phone", "chat"):
            total = sum(exp[r + "__daily"][ch] for r in reasons)
            weekend = dow >= 5
            curves = np.where(weekend[:, None], intraday_curve(True, n_int), intraday_curve(False, n_int))
            noisy = curves * rng.lognormal(0, 0.08, curves.shape)
            noisy /= noisy.sum(axis=1, keepdims=True)
            counts = np.array([rng.multinomial(total[i], noisy[i]) for i in range(n)])
            intraday_rows.append(
                pd.DataFrame(
                    {
                        "day": np.repeat(days, n_int),
                        "market": m,
                        "channel": ch,
                        "interval": np.tile(np.arange(n_int), n),
                        "contacts": counts.ravel(),
                    }
                )
            )

    shutil.rmtree(RAW, ignore_errors=True)
    shutil.rmtree(TRUTH, ignore_errors=True)
    RAW.mkdir(parents=True)
    TRUTH.mkdir(parents=True)
    tables = {
        "orders": pd.concat(orders_rows),
        "order_plan": pd.concat(plan_rows),
        "contacts_daily": pd.concat(contact_rows),
        "contacts_intraday": pd.concat(intraday_rows),
        "holidays": hol,
        "campaigns": camp,
    }
    for name, df in tables.items():
        df.to_parquet(RAW / f"{name}.parquet", index=False)
    truth = {
        "incidents": incidents_rows,
        "bot": {"launch": bot["launch"], "markets": bot["markets"], "wismo_effect": bot["wismo_effect"]},
        "rates": rates,
    }
    (TRUTH / "truth.json").write_text(json.dumps(truth, indent=1))
    return {k: len(v) for k, v in tables.items()}
