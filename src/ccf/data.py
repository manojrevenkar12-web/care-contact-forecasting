"""Everything a forecaster may read, loaded once from the warehouse as arrays: contacts per series and day,
orders actual and planned per market and day, and the calendar. Never the truth."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np
import pandas as pd

from ccf.etl.run import connect

REASON_SOURCE = {"lounge": "lounge", "account_other": None}  # every other reason follows fashion orders


@dataclass
class Store:
    days: pd.DatetimeIndex
    series: list[str]  # market|channel|reason
    y: np.ndarray  # [series, day] contacts
    markets: list[str]
    orders: dict[str, np.ndarray]  # app -> [market, day] actual
    plan: dict[str, np.ndarray]  # app -> [market, day] planned
    cal: dict[str, np.ndarray]  # field -> [market, day]
    intraday: np.ndarray  # [market, channel(phone, chat), day, slot]

    def index(self, day) -> int:
        return int(self.days.get_loc(pd.Timestamp(day)))

    def parts(self, s: int) -> tuple[str, str, str]:
        m, c, r = self.series[s].split("|")
        return m, c, r

    def orders_known(self, app: str, origin: int, upto: int) -> np.ndarray:
        """Orders as a planner at `origin` knows them: actual before the origin, the plan from it on."""
        out = self.orders[app][:, :upto].astype(float).copy()
        out[:, origin:upto] = self.plan[app][:, origin:upto]
        return out


@cache
def load() -> Store:
    con = connect()
    c = con.execute("SELECT series, day, contacts FROM mart_contacts ORDER BY series, day").df()
    days = pd.DatetimeIndex(sorted(c["day"].unique()))
    series = sorted(c["series"].unique())
    y = c.pivot(index="series", columns="day", values="contacts").loc[series].to_numpy(dtype=float)
    o = con.execute("SELECT * FROM mart_orders ORDER BY market, day").df()
    markets = sorted(o["market"].unique())

    def wide(df, col):
        return df.pivot(index="market", columns="day", values=col).loc[markets].to_numpy(dtype=float)

    orders = {"fashion": wide(o, "fashion_orders"), "lounge": wide(o, "lounge_orders")}
    plan = {"fashion": wide(o, "fashion_plan"), "lounge": wide(o, "lounge_plan")}
    cal = con.execute("SELECT * FROM dim_calendar ORDER BY market, day").df()
    cal["campaign_code"] = cal["campaign"].map({"cyber_week": 1, "season_sale": 2}).fillna(0)
    cal["day_of_campaign"] = cal["day_of_campaign"].fillna(-1)
    fields = {f: wide(cal, f) for f in ("weekday", "day_of_year", "is_holiday", "is_after_holiday", "campaign_code", "day_of_campaign")}
    i = con.execute("SELECT market, channel, day, slot, contacts FROM mart_intraday ORDER BY market, channel, day, slot").df()
    n_slots = int(i["slot"].max()) + 1
    intr = np.zeros((len(markets), 2, len(days), n_slots))
    mi = {m: k for k, m in enumerate(markets)}
    ci = {"phone": 0, "chat": 1}
    di = {d: k for k, d in enumerate(days)}
    intr[i["market"].map(mi).to_numpy(), i["channel"].map(ci).to_numpy(), i["day"].map(di).to_numpy(), i["slot"].to_numpy()] = i["contacts"].to_numpy()
    con.close()
    return Store(days, series, y, markets, orders, plan, fields, intr)
