"""Analyses for the operations team, each read from the same driver fits:

- incidents: days whose contacts the drivers cannot explain (a carrier strike, an outage), flagged as they happen;
- the bot experiment: what the self-service bot did to where-is-my-order contacts, by difference in differences
  against the markets without it;
- why the next weeks look the way they do: the forecast split into what each reason and its orders contribute.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ccf.data import Store


def incident_flags(flags: dict, store: Store, since: int, until: int) -> set[tuple[str, str, str]]:
    """(market, reason, day) flagged between `since` and `until` (exclusive)."""
    out = set()
    for (m, r), days in flags.items():
        for d in days:
            if since <= d < until:
                out.add((m, r, str(store.days[d].date())))
    return out


def bot_experiment(
    store: Store, launch: str, treated: list[str], pre_days: int = 180, gap_days: int = 14, post_until: str | None = None, seed: int = 0
) -> dict:
    """Difference in differences on log(where-is-my-order contacts per fashion order four days earlier), weekly."""
    li = store.index(launch)
    end = store.index(post_until) if post_until else len(store.days)
    rows = []
    for m in store.markets:
        idx = [i for i, s in enumerate(store.series) if s.startswith(f"{m}|") and s.endswith("|wismo")]
        y = store.y[idx].sum(axis=0)
        o = np.roll(store.orders["fashion"][store.markets.index(m)], 4)
        for start in range(li - pre_days, end - 6, 7):
            if li <= start < li + gap_days:
                continue
            sl = slice(start, start + 7)
            rows.append({"market": m, "treated": m in treated, "post": start >= li, "rate": np.log(y[sl].sum() / o[sl].sum()), "week": start})
    df = pd.DataFrame(rows)

    def did(d: pd.DataFrame) -> float:
        g = d.groupby(["treated", "post"])["rate"].mean()
        return (g[(True, True)] - g[(True, False)]) - (g[(False, True)] - g[(False, False)])

    est = did(df)
    rng = np.random.default_rng(seed)
    weeks = df["week"].unique()
    boots = []
    for _ in range(400):
        pick = rng.choice(weeks, len(weeks), replace=True)
        boots.append(did(pd.concat([df[df.week == w] for w in pick])))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "effect": float(np.expm1(est)),
        "ci": [float(np.expm1(lo)), float(np.expm1(hi))],
        "weeks_pre": int((~df.post).sum() / len(store.markets)),
        "weeks_post": int(df.post.sum() / len(store.markets)),
        "treated": treated,
    }


def decompose(fits: dict, store: Store, origin: int, horizon: int) -> list[dict]:
    """Per forecast day: contacts from each reason, and for order-driven reasons, from orders of the last week
    against orders older than a week (the returns wave)."""
    out = []
    for h in range(horizon):
        day = {"day": str(store.days[origin + h].date())}
        for (_m, r), (fit, x, f) in fits.items():
            contrib = fit.beta[:, None] * x * f[None, :]
            names = fit.names
            recent = sum(contrib[i, h] for i, n in enumerate(names) if n.startswith(("fashion orders", "lounge orders")) and _lag_hi(n) <= 7)
            older = sum(contrib[i, h] for i, n in enumerate(names) if n.startswith(("fashion orders", "lounge orders")) and _lag_hi(n) > 7)
            base = sum(contrib[i, h] for i, n in enumerate(names) if not n.startswith(("fashion orders", "lounge orders")))
            day[r] = day.get(r, 0.0) + float(recent + older + base)
            day["orders_last_7_days"] = day.get("orders_last_7_days", 0.0) + float(recent)
            day["orders_8_to_28_days"] = day.get("orders_8_to_28_days", 0.0) + float(older)
            day["baseline"] = day.get("baseline", 0.0) + float(base)
        out.append(day)
    return out


def _lag_hi(name: str) -> int:
    part = name.split("orders ", 1)[1].split(" days")[0]
    return int(part.split("-")[-1])
