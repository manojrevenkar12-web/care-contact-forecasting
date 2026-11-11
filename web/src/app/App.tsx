import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import { Drivers } from "../features/drivers/Drivers";
import { Forecast } from "../features/forecast/Forecast";
import { Incidents } from "../features/incidents/Incidents";
import { Models } from "../features/models/Models";
import type { Run, Summary } from "../shared/data/types";
import { type Fetcher, useJson } from "../shared/data/useJson";
import { int, pct } from "../shared/format";
import { color, measure, motion as m, size, space, weight } from "../shared/theme/tokens";
import { EmptyNotice, ErrorNotice } from "../shared/ui/Notice";
import { Section } from "../shared/ui/Section";
import { Segmented } from "../shared/ui/Segmented";
import { Skeleton } from "../shared/ui/Skeleton";

const DATA = "data/summary.json";
const browserFetch: Fetcher = (u) => fetch(u);
const COMMAND = "make eval && make report";

function Lede({ run, labels }: { run: Run; labels: Record<string, string> }) {
  const c = run.models[run.chosen];
  const naive = run.models["seasonal_naive"];
  return (
    <p style={{ fontSize: size.lg, maxWidth: `${measure.text}ch`, margin: `${space[5]}px 0 0` }}>
      Six-week forecasts of contacts per market and channel from {run.origins.length} origins. The {labels[run.chosen].toLowerCase()} is off by {pct(c.wape)} a day,
      against {pct(naive.wape)} for last week repeated, and staffing from it keeps {pct(c.service_level_met, 0)} of half hours on target with{" "}
      {int(c.agent_hours)} agent hours.
    </p>
  );
}

export function Dashboard({ summary }: { summary: Summary }) {
  const reduce = useReducedMotion();
  const [split, setSplit] = useState<"heldout" | "dev">(summary.heldout ? "heldout" : "dev");
  const run = summary[split];
  return (
    <main style={{ maxWidth: measure.page, margin: "0 auto", padding: `${space[7]}px ${space[5]}px ${space[8]}px` }}>
      <motion.header initial={reduce ? false : { opacity: 0, y: space[2] }} animate={{ opacity: 1, y: 0 }} transition={{ duration: m.fast * 2, ease: m.ease }}>
        <p style={{ margin: 0, color: color.muted, fontSize: size.sm }}>care-contact-forecasting</p>
        <h1 style={{ fontSize: size.xxl, lineHeight: 1.08, letterSpacing: "-0.02em", fontWeight: weight.bold, margin: `${space[3]}px 0 0`, maxWidth: "22ch" }}>
          How many contacts next week, and how many people to answer them.
        </h1>
        {run && <Lede run={run} labels={summary.labels} />}
        <div style={{ marginTop: space[5] }}>
          <Segmented
            label="Which origins"
            value={split}
            onChange={setSplit}
            options={[
              { value: "heldout", label: "Held-out: Q4 with Cyber Week" },
              { value: "dev", label: "Development" },
            ]}
          />
        </div>
      </motion.header>
      {!run ? (
        <div style={{ marginTop: space[7] }}>
          <EmptyNotice what={split === "heldout" ? "held-out results" : "development results"} command={split === "heldout" ? "make heldout && make report" : COMMAND} />
        </div>
      ) : (
        <>
          <Section title="The forecast against what came" lede="The last origin of this run, at the grain capacity planning staffs. Pick a market and a channel.">
            <Forecast run={run} />
          </Section>
          <Section title="Models, scored by the staffing they buy" lede="Forecast error alone does not say what a model costs. Each forecast is turned into agents per half hour and run against the contacts that came.">
            <Models run={run} labels={summary.labels} />
          </Section>
          <Section title="Why the coming weeks look like this" lede="The same forecast for all markets, split by contact reason; the driver model knows which orders each contact follows.">
            <Drivers run={run} reasons={summary.reasons} />
          </Section>
          <Section title="Incidents and experiments">
            <Incidents run={run} />
          </Section>
        </>
      )}
      <footer style={{ borderTop: `1px solid ${color.line}`, paddingTop: space[5], marginTop: space[7], color: color.muted, fontSize: size.sm, maxWidth: `${measure.text}ch` }}>
        A simulated retailer with ten markets, six contact reasons and three channels; orders, the order plan and the calendar are known in advance, incidents are not.
        Reproduce with <code>{COMMAND}</code>.
      </footer>
    </main>
  );
}

export function App({ fetcher = browserFetch }: { fetcher?: Fetcher }) {
  const data = useJson<Summary>(DATA, fetcher);
  const wrap = { maxWidth: measure.page, margin: "0 auto", padding: space[7] };
  if (data.state === "loading")
    return (
      <main style={wrap}>
        <Skeleton label="Loading results" rows={8} />
      </main>
    );
  if (data.state === "error")
    return (
      <main style={wrap}>
        <ErrorNotice message={data.message} onRetry={data.retry} />
      </main>
    );
  return <Dashboard summary={data.data} />;
}
