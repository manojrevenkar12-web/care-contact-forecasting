"""reports/*.json -> the dashboard's data (web/public/data/summary.json) and the README tables (printed)."""

import json

from ccf.config import REPORTS, ROOT, forecast

LABELS = {
    "seasonal_naive": "Last week repeated",
    "ets": "Holt-Winters (ETS)",
    "gbm": "LightGBM on calendar and orders",
    "driver": "Driver model (orders, lags, calendar)",
    "ensemble": "Driver and LightGBM averaged",
}
REASONS = {
    "wismo": "Where is my order",
    "delivery_issue": "Delivery issue",
    "return_refund": "Return or refund",
    "payment": "Payment",
    "lounge": "Lounge",
    "account_other": "Account and other",
}


def load(name):
    p = REPORTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def trim(r):
    keep = ("split", "origins", "models", "perfect_forecast", "perfect_daily_totals", "incidents", "bot_experiment", "decomposition", "story")
    return {**{k: r[k] for k in keep}, "chosen": forecast()["chosen_model"]}


def table(r):
    rows = [
        "| Model | Error (WAPE) | Cyber Week period | Bias | 80% band holds | Agent hours, week two | Hours misplaced | Answered late |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for k, v in sorted(r["models"].items(), key=lambda kv: kv[1]["wape"]):
        name = f"**{LABELS[k]}**" if k == forecast()["chosen_model"] else LABELS[k]
        cov = f"{v['interval_coverage']:.0%}" if v["interval_coverage"] is not None else "–"
        staffing = f"{v['agent_hours']:,.0f} | {v['hours_misplaced']:,.0f} | {v['late_share']:.1%}"
        rows.append(f"| {name} | {v['wape']:.1%} | {v['peak_wape']:.1%} | {v['bias']:+.1%} | {cov} | {staffing} |")
    p, d = r["perfect_forecast"], r["perfect_daily_totals"]
    rows.append(f"| Perfect daily totals, usual intraday shape | | | | | {d['agent_hours']:,.0f} | {d['hours_misplaced']:,.0f} | {d['late_share']:.1%} |")
    rows.append(f"| Perfect forecast, every half hour | | | | | {p['agent_hours']:,.0f} | 0 | {p['late_share']:.1%} |")
    inc, b = r["incidents"], r["bot_experiment"]
    rows += [
        "",
        f"Incidents flagged as they happened: {inc['found']} of {inc['true']} found, {inc['flagged'] - inc['found']} false alarms "
        f"(precision {inc['precision']:.0%}, recall {inc['recall']:.0%}).",
        f"Order-status bot, difference in differences: {b['effect']:+.1%} "
        f"(95% interval {b['ci'][0]:+.1%} to {b['ci'][1]:+.1%}); true effect {b['true_effect']:+.0%}.",
    ]
    return "\n".join(rows)


if __name__ == "__main__":
    dev, held = load("dev"), load("heldout")
    out = {"labels": LABELS, "reasons": REASONS, "dev": trim(dev) if dev else None, "heldout": trim(held) if held else None}
    target = ROOT / "web" / "public" / "data"
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(out))
    for name, r in (("heldout", held), ("dev", dev)):
        if r:
            print(f"\n### {name} ({len(r['origins'])} origins)\n\n{table(r)}")
