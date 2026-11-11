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
          Error at market × channel per day over six weeks; staffing for phone and chat in week two, Erlang C, 80% answered in 20 s (phone) or 60 s (chat).
        </caption>
        <thead>
          <tr>
            <th style={{ ...head, textAlign: "left" }}>Model</th>
            <th style={head}>Error (WAPE)</th>
            <th style={head}>Cyber Week period</th>
            <th style={head}>Bias</th>
            <th style={head}>80% band holds</th>
            <th style={head}>Agent hours</th>
            <th style={head}>Half hours on target</th>
            <th style={head}>Contacts answered late</th>
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
                <td style={cell}>{pct(v.service_level_met, 0)}</td>
                <td style={cell}>{pct(v.late_share)}</td>
              </tr>
            );
          })}
          <tr style={{ color: color.muted }}>
            <td style={{ ...cell, textAlign: "left" }}>If the forecast had been perfect</td>
            <td style={cell} />
            <td style={cell} />
            <td style={cell} />
            <td style={cell} />
            <td style={cell}>{int(p.agent_hours)}</td>
            <td style={cell}>{pct(p.service_level_met, 0)}</td>
            <td style={cell}>{pct(p.late_share)}</td>
          </tr>
        </tbody>
      </table>
      <p style={{ color: color.muted, fontSize: size.sm, marginTop: space[3] }}>
        At an assumed {eur(run.models[run.chosen].agent_cost_eur / run.models[run.chosen].agent_hours)} per outsourced agent hour.
      </p>
    </div>
  );
}
