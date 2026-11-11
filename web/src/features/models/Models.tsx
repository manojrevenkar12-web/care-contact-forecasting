import type { Run } from "../../shared/data/types";
import { eur, int, pct, signedPct } from "../../shared/format";
import { color, size, space, weight } from "../../shared/theme/tokens";

/** Every model, scored on forecast error and on the staffing it would have bought for week two. */
export function Models({ run, labels }: { run: Run; labels: Record<string, string> }) {
  const order = Object.entries(run.models).sort((a, b) => a[1].wape - b[1].wape);
  const p = run.perfect_forecast;
  const cell = { padding: `${space[2]}px ${space[3]}px`, borderTop: `1px solid ${color.line}`, textAlign: "right" as const, whiteSpace: "nowrap" as const };
  const head = { ...cell, borderTop: "none", fontWeight: weight.medium, color: color.muted };
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: size.sm, fontVariantNumeric: "tabular-nums" }}>
        <caption style={{ textAlign: "left", color: color.muted, paddingBottom: space[3] }}>
          Error at market × channel per day over six weeks. Staffing: phone and chat in week two, Erlang C for 80% answered in 20 s (phone) or 60 s (chat);
          misplaced hours are agent hours above or below what the contacts that came needed.
        </caption>
        <thead>
          <tr>
            <th style={{ ...head, textAlign: "left" }}>Model</th>
            <th style={head}>WAPE</th>
            <th style={head}>Cyber Week</th>
            <th style={head}>Bias</th>
            <th style={head}>Band holds</th>
            <th style={head}>Agent hours</th>
            <th style={head}>Misplaced hours</th>
            <th style={head}>Late</th>
          </tr>
        </thead>
        <tbody>
          {order.map(([k, v]) => {
            const mine = k === run.chosen;
            return (
              <tr key={k} style={{ fontWeight: mine ? weight.semibold : weight.regular }}>
                <td style={{ ...cell, textAlign: "left", color: mine ? color.forecast : color.ink }}>{labels[k] ?? k}</td>
                <td style={cell}>{pct(v.wape)}</td>
                <td style={cell}>{v.peak_wape === null ? "–" : pct(v.peak_wape)}</td>
                <td style={cell}>{signedPct(v.bias)}</td>
                <td style={cell}>{v.interval_coverage === null ? "–" : pct(v.interval_coverage, 0)}</td>
                <td style={cell}>{int(v.agent_hours)}</td>
                <td style={cell}>{int(v.hours_misplaced)}</td>
                <td style={cell}>{pct(v.late_share)}</td>
              </tr>
            );
          })}
          {[
            ["Perfect daily totals, usual intraday shape", run.perfect_daily_totals.agent_hours, run.perfect_daily_totals.hours_misplaced, run.perfect_daily_totals.late_share],
            ["Perfect forecast, every half hour", p.agent_hours, 0, p.late_share],
          ].map(([label, hours, misplaced, late]) => (
            <tr key={String(label)} style={{ color: color.muted }}>
              <td style={{ ...cell, textAlign: "left" }}>{label}</td>
              <td style={cell} colSpan={4} />
              <td style={cell}>{int(Number(hours))}</td>
              <td style={cell}>{int(Number(misplaced))}</td>
              <td style={cell}>{pct(Number(late))}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ color: color.muted, fontSize: size.sm, marginTop: space[3] }}>
        Even perfect daily totals misplace {int(run.perfect_daily_totals.hours_misplaced)} hours through the half-hour pattern; a forecast can only remove the
        rest. At an assumed {eur(run.models[run.chosen].agent_cost_eur / run.models[run.chosen].agent_hours)} per outsourced agent hour.
      </p>
    </div>
  );
}
