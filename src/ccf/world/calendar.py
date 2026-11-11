"""What every planner knows in advance: public holidays per market and the campaign calendar.

Holidays are the main fixed ones per country (a simplification of the real calendars); Easter Monday is computed.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

COMMON = [(1, 1), (5, 1), (12, 25), (12, 26)]
NATIONAL = {
    "DE": [(10, 3)],
    "FR": [(7, 14), (11, 11)],
    "IT": [(6, 2), (8, 15)],
    "ES": [(10, 12), (8, 15)],
    "NL": [(4, 27)],
    "PL": [(5, 3), (11, 11)],
    "AT": [(10, 26), (12, 8)],
    "CH": [(8, 1)],
    "BE": [(7, 21)],
    "SE": [(6, 6)],
}
NO_MAY_DAY = {"NL", "CH"}


def easter(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def holidays(markets: list[str], years: list[int]) -> pd.DataFrame:
    rows = []
    for m in markets:
        for y in years:
            days = [(mm, dd) for mm, dd in COMMON if not (m in NO_MAY_DAY and (mm, dd) == (5, 1))] + NATIONAL[m]
            for mm, dd in days:
                rows.append((m, date(y, mm, dd)))
            rows.append((m, easter(y) + timedelta(days=1)))
            if m != "SE":
                rows.append((m, easter(y) - timedelta(days=2)))  # Good Friday
    df = pd.DataFrame(rows, columns=["market", "day"]).drop_duplicates()
    df["day"] = pd.to_datetime(df["day"])
    return df.sort_values(["market", "day"]).reset_index(drop=True)


def black_friday(year: int) -> date:
    nov1 = date(year, 11, 1)
    first_thu = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    return first_thu + timedelta(days=22)


def campaigns(years: list[int]) -> pd.DataFrame:
    """Cyber Week (Thursday before Black Friday to Cyber Monday) and the two end-of-season sales."""
    rows = []
    for y in years:
        bf = black_friday(y)
        for k in range(-1, 4):
            rows.append(("cyber_week", bf + timedelta(days=k), k))
        for start in (date(y, 6, 20), date(y, 12, 27)):
            for k in range(10):
                rows.append(("season_sale", start + timedelta(days=k), k))
    df = pd.DataFrame(rows, columns=["campaign", "day", "day_of_campaign"])
    df["day"] = pd.to_datetime(df["day"])
    return df
