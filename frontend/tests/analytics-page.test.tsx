import { screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

const SUMMARY = {
  run_count: 4,
  evaluated_count: 3,
  reviewed_count: 0,
  adjudicated_count: 0,
  configuration: { scope: "all", bootstrap_seed: 20260830, bootstrap_resamples: 2000 },
  metrics: [],
  primary_error_distribution: [],
  difficulty_table: [],
  efficiency: [
    {
      difficulty: "easy",
      outcome: "resolved",
      run_count: 3,
      runs_with_trajectory: 2,
      median_steps: 15.5,
      min_steps: 10,
      max_steps: 21,
      median_tool_calls: 13,
      provenance: "official",
    },
    {
      difficulty: "medium",
      outcome: "not_evaluated",
      run_count: 1,
      runs_with_trajectory: 0,
      median_steps: null,
      min_steps: null,
      max_steps: null,
      median_tool_calls: null,
      provenance: "official",
    },
  ],
  quadrant: [],
  observed_decline_interval: "not_observed",
  statistically_supported_decline_interval: "not_established",
  excluded_runs: [],
  cases: [],
};

test("the effort table reports medians, ranges, and missing trajectories", async () => {
  mockApi({ "/api/health": HEALTH, "/api/analytics/summary": SUMMARY });

  renderApp("/analytics");

  const section = await screen.findByLabelText("Agent effort");
  const easy = within(section).getByText("easy").closest("tr") as HTMLElement;
  expect(within(easy).getByText("3 (1 without trajectory)")).toBeInTheDocument();
  expect(within(easy).getByText("15.5")).toBeInTheDocument();
  expect(within(easy).getByText("10–21")).toBeInTheDocument();
  expect(within(easy).getByText("13")).toBeInTheDocument();

  const medium = within(section).getByText("medium").closest("tr") as HTMLElement;
  expect(within(medium).getByText("not evaluated")).toBeInTheDocument();
  expect(within(medium).getAllByText("—").length).toBeGreaterThanOrEqual(3);
});

test("an empty repository shows an honest empty state, not zeros", async () => {
  mockApi({
    "/api/health": HEALTH,
    "/api/analytics/summary": { ...SUMMARY, run_count: 0, efficiency: [] },
  });

  renderApp("/analytics");

  const section = await screen.findByLabelText("Agent effort");
  expect(within(section).getByText("No runs yet.")).toBeInTheDocument();
});
