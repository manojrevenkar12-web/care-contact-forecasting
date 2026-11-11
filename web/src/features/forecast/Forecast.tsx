import { useState } from "react";
import type { Run } from "../../shared/data/types";
import { pct, shortDate } from "../../shared/format";
import { color, font, measure, radius, size, space, weight } from "../../shared/theme/tokens";
import { Segmented } from "../../shared/ui/Segmented";
import { ForecastChart } from "./ForecastChart";

function Key({ swatch, dashed, text }: { swatch: string; dashed?: boolean; text: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: space[2] }}>
      <svg width={space[6]} height={space[3]} aria-hidden="true">
        <line x1={0} x2={space[6]} y1={space[3] / 2} y2={space[3] / 2} stroke={swatch} strokeWidth={dashed ? 1.5 : 2.5} strokeDasharray={dashed ? "5 4" : undefined} />
      </svg>
      {text}
    </span>
  );
}

export function Forecast({ run }: { run: Run }) {
  const s = run.story;
  const markets = [...new Set(s.keys.map((k) => k.split("|")[0]))];
  const [market, setMarket] = useState(markets.includes("DE") ? "DE" : markets[0]);
  const [channel, setChannel] = useState<"phone" | "chat" | "email">("phone");
  const row = s.keys.indexOf(`${market}|${channel}`);
  const act = s.actual[row];
  const fc = s.forecast[run.chosen][row];
  const wape = act.reduce((t, a, i) => t + Math.abs(fc[i] - a), 0) / act.reduce((t, a) => t + a, 0);
  const inside = act.filter((a, i) => a >= s.lower[row][i] && a <= s.upper[row][i]).length / act.length;
  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: space[4], alignItems: "center", marginBottom: space[4] }}>
        <label style={{ display: "inline-flex", gap: space[2], alignItems: "center", fontSize: size.sm }}>
          Market
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            style={{ font: `${weight.medium} ${size.sm}px ${font.body}`, padding: `${space[1]}px ${space[3]}px`, borderRadius: radius.md, border: `1px solid ${color.line}`, background: color.card }}
          >
            {markets.map((mk) => (
              <option key={mk}>{mk}</option>
            ))}
          </select>
        </label>
        <Segmented
          label="Channel"
          value={channel}
          onChange={setChannel}
          options={[
            { value: "phone", label: "Phone" },
            { value: "chat", label: "Chat" },
            { value: "email", label: "Email" },
          ]}
        />
      </div>
      <ForecastChart story={s} row={row} chosen={run.chosen} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: space[5], marginTop: space[3], fontSize: size.sm, color: color.muted, maxWidth: `${measure.text + 30}ch` }}>
        <Key swatch={color.actual} text="what came" />
        <Key swatch={color.forecast} text={`forecast made ${shortDate(s.origin)}, with 80% band`} />
        <Key swatch={color.naive} dashed text="last week repeated" />
        <span>
          {market} {channel}: {pct(wape)} error over six weeks; {pct(inside, 0)} of days inside the band.
        </span>
      </div>
    </div>
  );
}
