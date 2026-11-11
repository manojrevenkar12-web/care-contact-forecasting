// One source for colour, type, space and motion; components read only from here.
export const color = {
  paper: "#EEF1F4",
  card: "#FFFFFF",
  ink: "#13202B",
  muted: "#56636F",
  line: "#D3D9DF",
  panel: "#E2E7EC",
  actual: "#13202B", // what came
  forecast: "#2A6FDB", // the chosen model
  band: "#2A6FDB",
  naive: "#9AA4AE",
  peak: "#F2E4CC", // Cyber Week and the weeks after
  good: "#1E7A55",
  bad: "#B4432A",
  focus: "#2A6FDB",
  reasons: ["#2A6FDB", "#6D8FC7", "#1E7A55", "#B4432A", "#8C6A1F", "#7B6A9C"],
} as const;

export const font = { body: '"Onest", system-ui, sans-serif', code: 'ui-monospace, Menlo, monospace' } as const;
export const size = { xs: 12, sm: 14, md: 16, lg: 19, xl: 26, xxl: 44 } as const;
export const weight = { regular: 400, medium: 500, semibold: 600, bold: 700 } as const;
export const space = [0, 4, 8, 12, 16, 24, 32, 48, 64, 96] as const;
export const radius = { sm: 4, md: 8, pill: 999 } as const;
export const measure = { text: 68, page: 1120, chartHeight: 320, barHeight: 180, axis: 44, dot: 5 } as const;
export const breakpoint = { narrow: 720 } as const;
export const motion = { fast: 0.2, slow: 1.1, ease: [0.22, 1, 0.36, 1] as const } as const;
