import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App, Dashboard } from "../src/app/App";
import type { Summary } from "../src/shared/data/types";
import raw from "../public/data/summary.json";

const summary = raw as unknown as Summary;
const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response);
afterEach(cleanup);

describe("states", () => {
  it("shows a skeleton while loading", () => {
    render(<App fetcher={() => new Promise<Response>(() => {})} />);
    expect(screen.getByRole("status", { name: "Loading results" })).toBeTruthy();
  });
  it("explains a failure and retries", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ ok: false, status: 503 } as Response).mockImplementation(() => ok(summary));
    render(<App fetcher={fetcher as unknown as (u: string) => Promise<Response>} />);
    expect((await screen.findByRole("alert")).textContent).toContain("503");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toBeTruthy());
  });
  it("names the command when there are no results", () => {
    render(<Dashboard summary={{ ...summary, dev: null, heldout: null }} />);
    expect(screen.getAllByText(/make (eval|heldout) && make report/, { selector: "code" }).length).toBe(2);
  });
});

describe("content", () => {
  it("draws the forecast for the chosen market and channel", () => {
    render(<Dashboard summary={summary} />);
    const chart = screen.getAllByRole("img")[0];
    expect(chart.getAttribute("aria-label")).toMatch(/^DE phone/);
    fireEvent.click(screen.getByRole("radio", { name: "Chat" }));
    expect(screen.getAllByRole("img")[0].getAttribute("aria-label")).toMatch(/^DE chat/);
  });
  it("lists every model with its staffing", () => {
    render(<Dashboard summary={summary} />);
    const run = summary.heldout ?? summary.dev!;
    expect(screen.getAllByRole("row").length).toBe(Object.keys(run.models).length + 3); // header + two perfect references
  });
});
