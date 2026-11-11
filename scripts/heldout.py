"""Once: the backtest on the held-out origins (Q4 with Cyber Week) -> reports/heldout.json. Interval widths come
from the development run. Refuses to overwrite an earlier run."""

import json
import sys

from ccf.config import REPORTS
from ccf.evals.backtest import gate, run

if __name__ == "__main__":
    if (REPORTS / "heldout.json").exists() and "--i-know" not in sys.argv:
        sys.exit("reports/heldout.json exists: the held-out origins are run once (see docs/heldout-exposure.md)")
    dev = json.loads((REPORTS / "dev.json").read_text())
    r = run("heldout", interval_quantiles=dev["interval_quantiles"])
    for m, v in r["models"].items():
        print(f"{m:15s} wape {v['wape']:.3f} peak {v['peak_wape']:.3f} bias {v['bias']:+.3f} cov {v['interval_coverage']}", end=" ")
        print(f"hours {v['agent_hours']:.0f} SL met {v['service_level_met']:.3f} late {v['late_share']:.3f}")
    print("perfect", r["perfect_forecast"])
    print("incidents", {k: v for k, v in r["incidents"].items() if k not in ("missed", "false_alarms")})
    fails = gate(r)
    print("GATE", "PASS" if not fails else "FAIL: " + "; ".join(fails))
