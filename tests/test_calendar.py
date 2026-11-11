from datetime import date

from ccf.world.calendar import black_friday, campaigns, easter, holidays


def test_easter_and_black_friday():
    assert easter(2024) == date(2024, 3, 31) and easter(2025) == date(2025, 4, 20)
    assert black_friday(2025) == date(2025, 11, 28) and black_friday(2024) == date(2024, 11, 29)


def test_calendar_tables():
    h = holidays(["DE", "NL"], [2025])
    assert date(2025, 10, 3) in set(h[h.market == "DE"].day.dt.date)
    assert date(2025, 5, 1) not in set(h[h.market == "NL"].day.dt.date)
    c = campaigns([2025])
    assert set(c[c.campaign == "cyber_week"].day.dt.date) == {date(2025, 11, d) for d in range(27, 31)} | {date(2025, 12, 1)}
