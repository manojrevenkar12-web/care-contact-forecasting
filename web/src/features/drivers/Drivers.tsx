import type { Run } from "../../shared/data/types";
import { int, shortDate } from "../../shared/format";
import { color, measure, size, space } from "../../shared/theme/tokens";

/** The forecast for all markets and channels, day by day, split into contact reasons: what operations asks
 * when the numbers jump ("why does next Monday need so many people?"). */
export function Drivers({ run, reasons }: { run: Run; reasons: Record<string, string> }) {
  const keys = Object.keys(reasons);
  const days = run.decomposition.days;
  const totals = days.map((d) => keys.reduce((s, k) => s + Number(d[k] ?? 0), 0));
  const max = Math.max(...totals) * 1.05;
  const W = 1000;
  const H = measure.barHeight;
  const bw = W / days.length;
  const peakDay = days[totals.indexOf(Math.max(...totals))];
  const recent = Number(peakDay.orders_last_7_days);
  const older = Number(peakDay.orders_8_to_28_days);
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H + space[5]}`} role="img" aria-label={`Forecast contacts by reason from ${shortDate(run.decomposition.origin)}`} style={{ width: "100%", height: "auto" }}>
        {days.map((d, i) => {
          let acc = 0;
          return (
            <g key={String(d.day)}>
              {keys.map((k, j) => {
                const v = Number(d[k] ?? 0);
                const h = (v / max) * H;
                acc += h;
                return <rect key={k} x={i * bw + 1} width={bw - 2} y={H - acc} height={h} fill={color.reasons[j % color.reasons.length]} />;
              })}
              {i % 7 === 0 && (
                <text x={i * bw + bw / 2} y={H + space[4]} fontSize={size.xs} fill={color.muted} textAnchor="middle">
                  {shortDate(String(d.day))}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <p style={{ display: "flex", flexWrap: "wrap", gap: space[4], fontSize: size.sm, color: color.muted, margin: `${space[3]}px 0` }}>
        {keys.map((k, j) => (
          <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: space[2] }}>
            <span aria-hidden="true" style={{ width: space[3], height: space[3], background: color.reasons[j % color.reasons.length] }} />
            {reasons[k]}
          </span>
        ))}
      </p>
      <p style={{ margin: 0, maxWidth: `${measure.text}ch` }}>
        The busiest forecast day, {shortDate(String(peakDay.day))}, needs about {int(Math.max(...totals))} contacts answered: {int(recent)} from orders of the
        week before and {int(older)} from orders one to four weeks earlier, mostly returns and refunds.
      </p>
    </div>
  );
}
