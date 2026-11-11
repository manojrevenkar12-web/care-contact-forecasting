import type { Run } from "../../shared/data/types";
import { pct, signedPct } from "../../shared/format";
import { color, measure, size, space, weight } from "../../shared/theme/tokens";

/** Incident days flagged as they happened, and what the self-service bot did, by difference in differences. */
export function Incidents({ run }: { run: Run }) {
  const inc = run.incidents;
  const b = run.bot_experiment;
  const scale = (v: number) => ((v + 0.4) / 0.5) * 100; // -40% .. +10%
  return (
    <div style={{ display: "grid", gap: space[7], gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
      <div>
        <h3 style={{ fontSize: size.lg, margin: `0 0 ${space[2]}px` }}>Incidents, flagged as they happened</h3>
        <p style={{ margin: 0, color: color.muted, maxWidth: `${measure.text}ch` }}>
          Days a carrier strike or an outage pushed one reason far above what orders explain. Flagged days are kept out of model training.
        </p>
        <p style={{ fontSize: size.xl, fontWeight: weight.semibold, margin: `${space[4]}px 0 ${space[1]}px`, fontVariantNumeric: "tabular-nums" }}>
          {inc.found} of {inc.true} found, {inc.flagged - inc.found} false
        </p>
        <p style={{ margin: 0, color: color.muted, fontSize: size.sm }}>
          Precision {pct(inc.precision, 0)}, recall {pct(inc.recall, 0)}, by market, reason and day.
          {inc.missed.length > 0 && ` Missed: ${inc.missed.slice(0, 4).map((x) => x.replaceAll("|", " ")).join("; ")}.`}
        </p>
      </div>
      <div>
        <h3 style={{ fontSize: size.lg, margin: `0 0 ${space[2]}px` }}>What the order-status bot did</h3>
        <p style={{ margin: 0, color: color.muted, maxWidth: `${measure.text}ch` }}>
          Where-is-my-order contacts per order in {b.treated.join(", ")} against the other markets, {b.weeks_pre} weeks before the launch and {b.weeks_post} after.
        </p>
        <svg viewBox="0 0 100 18" role="img" aria-label={`Estimated ${signedPct(b.effect)}, true ${signedPct(b.true_effect)}`} style={{ width: "100%", height: "auto", marginTop: space[4] }}>
          <line x1={0} x2={100} y1={9} y2={9} stroke={color.line} strokeWidth={0.4} />
          <line x1={scale(0)} x2={scale(0)} y1={3} y2={15} stroke={color.muted} strokeWidth={0.3} />
          <line x1={scale(b.ci[0])} x2={scale(b.ci[1])} y1={9} y2={9} stroke={color.forecast} strokeWidth={1.6} />
          <circle cx={scale(b.effect)} cy={9} r={1.8} fill={color.forecast} />
          <line x1={scale(b.true_effect)} x2={scale(b.true_effect)} y1={4} y2={14} stroke={color.ink} strokeWidth={0.6} />
        </svg>
        <p style={{ margin: 0, fontSize: size.sm }}>
          Estimated <strong>{signedPct(b.effect)}</strong> (95% interval {signedPct(b.ci[0])} to {signedPct(b.ci[1])}); the simulation's true effect is {signedPct(b.true_effect)} (black mark).
        </p>
      </div>
    </div>
  );
}
