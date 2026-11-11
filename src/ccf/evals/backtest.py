"""The backtest: forecasts from rolling origins, scored at the grain capacity planning uses (market x channel per
day), with prediction intervals, the staffing each forecast would have bought, incident flags and the bot experiment.
Only this module reads the truth."""

from __future__ import annotations

import json
import time
from datetime import date, timedelta

import numpy as np

from ccf.analysis.insights import bot_experiment, decompose, incident_flags
from ccf.config import REPORTS, TRUTH, forecast, world
from ccf.data import Store, load
from ccf.models.forecasters import MODELS, all_forecasts
from ccf.staffing.plan import evaluate as staffing
from ccf.world.calendar import black_friday

BUCKETS = 6  # horizon weeks


def origins(split: str) -> list[str]:
    o = forecast()["backtest"][f"{split}_origins"]
    d, last, out = date.fromisoformat(o["first"]), date.fromisoformat(o["last"]), []
    while d <= last:
        out.append(str(d))
        d += timedelta(days=o["every_days"])
    return out


def grain(store: Store, a: np.ndarray) -> tuple[np.ndarray, list[str]]:
    keys = sorted({"|".join(s.split("|")[:2]) for s in store.series})
    rows = [a[[i for i, s in enumerate(store.series) if s.startswith(k + "|")]].sum(axis=0) for k in keys]
    return np.array(rows), keys


def peak_days(store: Store) -> set[int]:
    """Cyber Week and the two weeks after it, when where-is-my-order and return contacts arrive."""
    out = set()
    for y in sorted(set(store.days.year)):
        bf = store.days.get_indexer([np.datetime64(black_friday(y))])[0]
        if bf >= 0:
            out.update(range(bf - 1, bf + 15))
    return out


def run(split: str, interval_quantiles: dict | None = None) -> dict:
    t0 = time.perf_counter()
    store = load()
    cfg = forecast()
    H = cfg["backtest"]["horizon"]
    alpha = (1 - cfg["intervals"]["coverage"]) / 2
    truth = json.loads((TRUTH / "truth.json").read_text())
    true_incidents = {(r["market"], r["reason"], r["day"]) for r in truth["incidents"]}
    step = cfg["backtest"][f"{split}_origins"]["every_days"]
    peaks = peak_days(store)

    err = {m: np.zeros(BUCKETS) for m in MODELS}
    act_sum = np.zeros(BUCKETS)
    bias = {m: 0.0 for m in MODELS}
    peak_err = {m: 0.0 for m in MODELS}
    peak_act = 0.0
    resid: dict[str, list[list[np.ndarray]]] = {m: [[] for _ in range(BUCKETS)] for m in MODELS}
    covered = {m: [0, 0] for m in MODELS}
    staff = {}
    flagged_all, truth_windows = set(), set()
    per_origin = []
    decomposition = None
    story = None
    for k, day in enumerate(origins(split)):
        o = store.index(day)
        fc, fits, flags = all_forecasts(store, o, H)
        A, keys = grain(store, store.y[:, o : o + H])
        row = {"origin": day}
        for m, f in fc.items():
            F, _ = grain(store, f)
            for b in range(BUCKETS):
                sl = slice(7 * b, 7 * b + 7)
                err[m][b] += np.abs(F[:, sl] - A[:, sl]).sum()
                r = np.log((A[:, sl] + 1) / (F[:, sl] + 1))
                q = None
                if interval_quantiles is not None:
                    q = interval_quantiles[m][b]
                elif k >= cfg["intervals"]["min_origins"]:
                    pool = np.concatenate([x.ravel() for x in resid[m][b]])
                    q = np.quantile(pool, [alpha, 1 - alpha])
                if q is not None:
                    covered[m][0] += int(((r >= q[0]) & (r <= q[1])).sum())
                    covered[m][1] += r.size
                resid[m][b].append(r)
            bias[m] += (F - A).sum()
            pk = [h for h in range(H) if o + h in peaks]
            if pk:
                peak_err[m] += np.abs(F[:, pk] - A[:, pk]).sum()
            row[m] = float(np.abs(F - A).sum() / A.sum())
        for b in range(BUCKETS):
            act_sum[b] += A[:, 7 * b : 7 * b + 7].sum()
        pk = [h for h in range(H) if o + h in peaks]
        if pk:
            peak_act += A[:, pk].sum()
        s = staffing(store, o, fc)
        for m, v in s.items():
            acc = staff.setdefault(m, {key: 0.0 for key in v})
            for key, val in v.items():
                acc[key] += val
        flagged_all |= incident_flags(flags, store, o - step, o)
        lo_day, hi_day = store.days[o - step], store.days[o - 1]
        truth_windows |= {t for t in true_incidents if lo_day <= np.datetime64(t[2]) <= hi_day}
        per_origin.append(row)
        decomposition = (decompose(fits, store, o, H), day)
        chosen = cfg["chosen_model"]
        Fc, _ = grain(store, fc[chosen])
        q = interval_quantiles[chosen] if interval_quantiles is not None else None
        if q is None and k >= cfg["intervals"]["min_origins"]:
            q = [np.quantile(np.concatenate([x.ravel() for x in resid[chosen][b][:-1]]), [alpha, 1 - alpha]).tolist() for b in range(BUCKETS)]
        lo_q = np.repeat([b[0] for b in q], 7)[:H] if q else np.zeros(H)
        hi_q = np.repeat([b[1] for b in q], 7)[:H] if q else np.zeros(H)
        story = {
            "origin": day,
            "days": [str(store.days[o + h].date()) for h in range(H)],
            "keys": keys,
            "actual": A.round().astype(int).tolist(),
            "forecast": {m: grain(store, f)[0].round(1).tolist() for m, f in fc.items()},
            "lower": (np.expm1(np.log1p(Fc) + lo_q)).round(1).tolist(),
            "upper": (np.expm1(np.log1p(Fc) + hi_q)).round(1).tolist(),
            "peak_days": [str(store.days[o + h].date()) for h in range(H) if o + h in peaks],
        }
        print(f"{split} {day}: " + " ".join(f"{m} {row[m]:.3f}" for m in MODELS), flush=True)

    total_act = act_sum.sum()
    models = {}
    eur = cfg["staffing"]["eur_per_agent_hour"]
    for m in MODELS:
        st = staff[m]
        models[m] = {
            "wape": float(err[m].sum() / total_act),
            "wape_by_week": [float(err[m][b] / act_sum[b]) for b in range(BUCKETS)],
            "bias": float(bias[m] / total_act),
            "peak_wape": float(peak_err[m] / peak_act) if peak_act else None,
            "interval_coverage": covered[m][0] / covered[m][1] if covered[m][1] else None,
            "agent_hours": st["agent_hours"],
            "agent_cost_eur": st["agent_hours"] * eur,
            "service_level_met": st["intervals_met"] / st["intervals"],
            "late_share": st["late"] / st["contacts"],
            "hours_over": st["hours_over"],
            "hours_short": st["hours_short"],
            "hours_misplaced": st["hours_over"] + st["hours_short"],
        }
    perfect = staff["perfect forecast"]
    daily_perfect = staff["perfect daily totals"]
    tp = len(flagged_all & truth_windows)
    report = {
        "split": split,
        "origins": origins(split),
        "horizon_days": H,
        "grain": "market x channel per day",
        "models": models,
        "perfect_forecast": {
            "agent_hours": perfect["agent_hours"],
            "agent_cost_eur": perfect["agent_hours"] * eur,
            "service_level_met": perfect["intervals_met"] / perfect["intervals"],
            "late_share": perfect["late"] / perfect["contacts"],
        },
        "perfect_daily_totals": {
            "agent_hours": daily_perfect["agent_hours"],
            "service_level_met": daily_perfect["intervals_met"] / daily_perfect["intervals"],
            "late_share": daily_perfect["late"] / daily_perfect["contacts"],
            "hours_over": daily_perfect["hours_over"],
            "hours_short": daily_perfect["hours_short"],
            "hours_misplaced": daily_perfect["hours_over"] + daily_perfect["hours_short"],
        },
        "incidents": {
            "flagged": len(flagged_all),
            "true": len(truth_windows),
            "found": tp,
            "precision": tp / len(flagged_all) if flagged_all else 1.0,
            "recall": tp / len(truth_windows) if truth_windows else 1.0,
            "missed": sorted("|".join(t) for t in truth_windows - flagged_all),
            "false_alarms": sorted("|".join(t) for t in flagged_all - truth_windows),
        },
        "bot_experiment": {
            **bot_experiment(store, truth["bot"]["launch"], truth["bot"]["markets"], post_until=world()["dev_cutoff"]),
            "true_effect": truth["bot"]["wismo_effect"],
        },
        "decomposition": {"origin": decomposition[1], "days": decomposition[0]},
        "story": story,
        "per_origin": per_origin,
        "interval_quantiles": {
            m: [np.quantile(np.concatenate([x.ravel() for x in resid[m][b]]), [alpha, 1 - alpha]).tolist() for b in range(BUCKETS)] for m in MODELS
        },
        "minutes": round((time.perf_counter() - t0) / 60, 1),
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{split}.json").write_text(json.dumps(report, indent=1))
    return report


def gate(report: dict) -> list[str]:
    g = forecast()["gate"]
    chosen = forecast()["chosen_model"]
    m, naive = report["models"][chosen], report["models"]["seasonal_naive"]
    fails = []
    if m["wape"] > g["max_wape_vs_naive"] * naive["wape"]:
        fails.append(f"{chosen} WAPE {m['wape']:.3f} is not below {g['max_wape_vs_naive']} x naive {naive['wape']:.3f}")
    cov = m["interval_coverage"]
    if cov is None or not g["coverage_low"] <= cov <= g["coverage_high"]:
        fails.append(f"80% interval coverage {cov}")
    if m["hours_misplaced"] > g["max_misplaced_vs_naive"] * naive["hours_misplaced"]:
        fails.append(f"{chosen} misplaced {m['hours_misplaced']:.0f} agent hours, not below {g['max_misplaced_vs_naive']} x naive")
    inc = report["incidents"]
    if inc["recall"] < g["min_anomaly_recall"]:
        fails.append(f"incident recall {inc['recall']:.2f}")
    if inc["precision"] < g["min_anomaly_precision"]:
        fails.append(f"incident precision {inc['precision']:.2f}")
    return fails
