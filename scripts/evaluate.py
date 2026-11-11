"""The backtest on the development origins -> reports/dev.json (~12 minutes)."""

from ccf.evals.backtest import gate, run

if __name__ == "__main__":
    r = run("dev")
    for m, v in r["models"].items():
        print(f"{m:15s} wape {v['wape']:.3f} peak {v['peak_wape']:.3f} bias {v['bias']:+.3f} cov {v['interval_coverage']}", end=" ")
        print(f"hours {v['agent_hours']:.0f} SL met {v['service_level_met']:.3f} late {v['late_share']:.3f}")
    print("perfect", r["perfect_forecast"])
    print("incidents", {k: v for k, v in r["incidents"].items() if k not in ("missed", "false_alarms")})
    print("missed", r["incidents"]["missed"][:20])
    print("false alarms", r["incidents"]["false_alarms"][:30])
    print("bot", r["bot_experiment"])
    fails = gate(r)
    print("GATE", "PASS" if not fails else "FAIL: " + "; ".join(fails))
