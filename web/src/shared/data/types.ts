export type ModelScore = {
  wape: number;
  wape_by_week: number[];
  bias: number;
  peak_wape: number | null;
  interval_coverage: number | null;
  agent_hours: number;
  agent_cost_eur: number;
  service_level_met: number;
  late_share: number;
  hours_over: number;
  hours_short: number;
  hours_misplaced: number;
};

export type Story = {
  origin: string;
  days: string[];
  keys: string[]; // market|channel
  actual: number[][];
  forecast: Record<string, number[][]>;
  lower: number[][];
  upper: number[][];
  peak_days: string[];
};

export type Run = {
  split: "dev" | "heldout";
  origins: string[];
  chosen: string;
  models: Record<string, ModelScore>;
  perfect_forecast: { agent_hours: number; agent_cost_eur: number; service_level_met: number; late_share: number };
  perfect_daily_totals: { agent_hours: number; hours_misplaced: number; late_share: number };
  incidents: { flagged: number; true: number; found: number; precision: number; recall: number; missed: string[]; false_alarms: string[] };
  bot_experiment: { effect: number; ci: [number, number]; true_effect: number; treated: string[]; weeks_pre: number; weeks_post: number };
  decomposition: { origin: string; days: Record<string, number | string>[] };
  story: Story;
};

export type Summary = { labels: Record<string, string>; reasons: Record<string, string>; dev: Run | null; heldout: Run | null };
