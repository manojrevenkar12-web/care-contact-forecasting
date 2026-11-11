import { motion, useReducedMotion } from "framer-motion";
import type { Story } from "../../shared/data/types";
import { int, shortDate } from "../../shared/format";
import { color, measure, motion as m, size, space } from "../../shared/theme/tokens";

const W = 1000;

/** Six weeks of daily contacts for one market and channel: what came, the forecast with its 80% band, and
 * last week repeated. Cyber Week and the two weeks after it are shaded. */
export function ForecastChart({ story, row, chosen }: { story: Story; row: number; chosen: string }) {
  const reduce = useReducedMotion();
  const H = measure.chartHeight;
  const pad = { l: measure.axis, r: space[4], t: space[4], b: space[6] };
  const actual = story.actual[row];
  const fc = story.forecast[chosen][row];
  const naive = story.forecast["seasonal_naive"][row];
  const lo = story.lower[row];
  const hi = story.upper[row];
  const n = story.days.length;
  const max = Math.max(...actual, ...hi, ...naive) * 1.08;
  const x = (i: number) => pad.l + (i / (n - 1)) * (W - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - v / max) * (H - pad.t - pad.b);
  const line = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const band = `${line(hi)} ${lo.map((v, i) => `L${x(n - 1 - i).toFixed(1)},${y(lo[n - 1 - i]).toFixed(1)}`).join(" ")} Z`;
  const peak = story.days.map((d, i) => (story.peak_days.includes(d) ? i : -1)).filter((i) => i >= 0);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round((max * t) / 100) * 100);
  const [market, channel] = story.keys[row].split("|");
  const wape = actual.reduce((s, a, i) => s + Math.abs(fc[i] - a), 0) / actual.reduce((s, a) => s + a, 0);
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${market} ${channel}: forecast from ${shortDate(story.origin)} against what came, ${(wape * 100).toFixed(1)}% error over six weeks`}
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {peak.length > 0 && <rect x={x(peak[0]) - 6} y={pad.t} width={x(peak[peak.length - 1]) - x(peak[0]) + 12} height={H - pad.t - pad.b} fill={color.peak} />}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke={color.line} />
          <text x={pad.l - space[2]} y={y(t) + 4} textAnchor="end" fontSize={size.xs} fill={color.muted}>
            {int(t)}
          </text>
        </g>
      ))}
      {story.days.map((d, i) =>
        i % 7 === 0 ? (
          <text key={d} x={x(i)} y={H - space[2]} fontSize={size.xs} fill={color.muted} textAnchor="middle">
            {shortDate(d)}
          </text>
        ) : null,
      )}
      <path d={band} fill={color.band} opacity={0.14} />
      <path d={line(naive)} fill="none" stroke={color.naive} strokeWidth={1.5} strokeDasharray="5 5" />
      <motion.path
        key={`${story.origin}-${row}`}
        d={line(fc)}
        fill="none"
        stroke={color.forecast}
        strokeWidth={2.5}
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: reduce ? 0 : m.slow, ease: m.ease }}
      />
      <path d={line(actual)} fill="none" stroke={color.actual} strokeWidth={1.5} />
      {actual.map((a, i) => (
        <circle key={i} cx={x(i)} cy={y(a)} r={measure.dot / 2 + 1} fill={color.actual} />
      ))}
    </svg>
  );
}
