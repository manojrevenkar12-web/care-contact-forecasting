# Held-out exposure

What anyone working on this repository has seen of the held-out period (forecasts from the eight Mondays
2025-09-29 to 2025-11-17, six weeks each, so October to the end of December 2025 including Cyber Week), and when.
The world and the held-out origins are pinned in `config/heldout.lock`.

- **2026-11-11, world generated and pinned.** The generator writes all three years at once, so the sanity check of
  the generated data printed total daily contacts for 20 November to 10 December 2025 (inside the held-out
  period) once, to confirm the Cyber Week wave looks right. No model, setting or threshold was chosen from it.
- **Development runs.** Three development backtests (origins up to 2025-08-25, forecasts up to 2025-10-05). The
  last development forecasts overlap the first held-out week; no held-out score was computed or looked at.
- **The held-out run (commit `e15d14b`, `reports/heldout.json`, never rewritten)**, after the development run at the
  same commit passed the gate. Driver model: 5.3% daily error at market x channel against 14.0% for last week
  repeated; 5.6% in the Cyber Week period against 24.0%; 80% band held on 77% of days. Staffing week two from it
  misplaced 15,092 agent hours (naive 16,950; perfect daily totals with the usual intraday shape 14,178). Incidents:
  13 of 16 found, no false alarms; the three-day NL carrier strike (21-23 October) was missed.
