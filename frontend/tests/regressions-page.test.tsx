import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { agreement } from "../src/pages/RegressionsPage";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

const CARD = {
  schema_version: "regression-card-v1",
  recorded_at: "2026-09-01T05:31:20+00:00",
  slice_id: "day8-slice-v1",
  note: "Frozen day8 evidence; the re-evaluation ran in memory.",
  stored_version: "workbench-evaluator-v1",
  reevaluated_version: "workbench-evaluator-v3",
  scores: {
    stored: {
      false_positives: { runs: ["run-b"], n: 1, d: 1 },
      detection: { runs: ["run-a"], n: 1, d: 1 },
      exact_localization: { runs: [], n: 0, d: 1 },
      within_one_localization: { runs: [], n: 0, d: 1 },
    },
    reevaluated: {
      false_positives: { runs: [], n: 0, d: 1 },
      detection: { runs: ["run-a"], n: 1, d: 1 },
      exact_localization: { runs: ["run-a"], n: 1, d: 1 },
      within_one_localization: { runs: ["run-a"], n: 1, d: 1 },
    },
  },
  runs: [
    {
      run_id: "run-a",
      task_id: "django__django-15278",
      human: { process_status: "invalid", first_error_step: 27 },
      stored: {
        evaluator_version: "workbench-evaluator-v1",
        status: "partial",
        process_status: "invalid",
        first_error_step: null,
      },
      reevaluated: {
        evaluator_version: "workbench-evaluator-v3",
        status: "completed",
        process_status: "invalid",
        first_error_step: 27,
        exclusions: [],
        semantic_condensation: "semantic-condense-v1: aggregated 40 passing per-test checks",
        protected_check: {
          status: "fail",
          summary: "modifies 'tests/schema/tests.py' via relative path",
        },
      },
    },
    {
      run_id: "run-b",
      task_id: "django__django-14631",
      human: { process_status: "valid", first_error_step: null },
      stored: {
        evaluator_version: "workbench-evaluator-v1",
        status: "partial",
        process_status: "invalid",
        first_error_step: 13,
      },
      reevaluated: {
        evaluator_version: "workbench-evaluator-v3",
        status: "completed",
        process_status: "valid",
        first_error_step: null,
        exclusions: [],
        semantic_condensation: null,
        protected_check: { status: "warning", summary: "reverted before submission" },
      },
    },
  ],
};

const STABILITY = {
  schema_version: "judge-stability-v1",
  recorded_at: "2026-08-31T16:21:19+00:00",
  subject: "django__django-16899__yJvk3qg__agent",
  repeats: 2,
  judge: {
    model: "hy3",
    reasoning_effort: "high",
    temperature: 0.9,
    top_p: 1.0,
    rubric_version: "process-rubric-v1",
    semantic_prompt_version: "semantic-prompt-v1",
  },
  summary: {
    completed: 2,
    verdict_unanimous: true,
    verdicts: ["invalid"],
    first_error_steps: [13],
    step_unanimous: true,
  },
  attempts: [
    {
      attempt: 1,
      status: "completed",
      process_status: "invalid",
      first_error_location: "located",
      first_error_step: 13,
      primary_category: "process_integrity",
      finding_count: 2,
      repair_retries: 0,
    },
    {
      attempt: 2,
      status: "completed",
      process_status: "invalid",
      first_error_location: "located",
      first_error_step: 13,
      primary_category: "process_integrity",
      finding_count: 1,
      repair_retries: 1,
    },
  ],
};

const LIBRARY = {
  regression_cards: [{ file: "results/regression/day11-regression-card-v3.json", card: CARD }],
  judge_stability: [{ file: "results/judge-stability/django__django-16899.json", record: STABILITY }],
  unreadable: [],
};

test("a regression card renders its scores with change direction", async () => {
  mockApi({ "/api/health": HEALTH, "/api/regressions": LIBRARY });

  renderApp("/regressions");

  expect(
    await screen.findByText("workbench-evaluator-v1 → workbench-evaluator-v3"),
  ).toBeInTheDocument();

  const falsePositives = screen
    .getByText("False positives (lower is better)")
    .closest("tr") as HTMLElement;
  expect(within(falsePositives).getByText("1 / 1")).toBeInTheDocument();
  expect(within(falsePositives).getByText("0 / 1")).toBeInTheDocument();
  expect(within(falsePositives).getByText("improved")).toHaveClass("chip-pass");

  const detection = screen.getByText("Invalid-process detection").closest("tr") as HTMLElement;
  expect(within(detection).getByText("unchanged")).toBeInTheDocument();
});

test("per-run rows compare both evaluator versions against the human label", async () => {
  mockApi({ "/api/health": HEALTH, "/api/regressions": LIBRARY });

  renderApp("/regressions");

  const link = await screen.findByRole("link", { name: "django__django-15278" });
  expect(link).toHaveAttribute("href", "/runs/run-a");

  // run-a: v1 found the right verdict but not the step; v3 matches exactly.
  expect(screen.getByText("step differs")).toHaveClass("chip-warning");
  // run-b: v1 was a false positive; v3 agrees with the human "valid".
  expect(screen.getByText("differs from human")).toHaveClass("chip-fail");
  expect(screen.getAllByText("matches human")).toHaveLength(2);
});

test("the evidence expander shows protected-path and condensation detail", async () => {
  mockApi({ "/api/health": HEALTH, "/api/regressions": LIBRARY });

  renderApp("/regressions");

  await screen.findByText("workbench-evaluator-v1 → workbench-evaluator-v3");
  expect(screen.getByText("condensed input")).not.toBeVisible();

  fireEvent.click(screen.getAllByText("evidence")[0]);

  expect(screen.getByText("condensed input")).toBeVisible();
  expect(screen.getByText(/modifies 'tests\/schema\/tests\.py' via relative path/)).toBeVisible();
  expect(screen.getByText("protected paths fail")).toHaveClass("chip-fail");
});

test("an honest abstention is labeled as such, not as a wrong verdict", () => {
  const human = { process_status: "valid", first_error_step: null };
  expect(agreement({ process_status: "inconclusive", first_error_step: null }, human)).toEqual({
    label: "abstained",
    chip: "chip-warning",
  });
  expect(agreement({ process_status: "invalid", first_error_step: 3 }, human)).toEqual({
    label: "differs from human",
    chip: "chip-fail",
  });
  expect(agreement({ process_status: "valid", first_error_step: null }, human)).toEqual({
    label: "matches human",
    chip: "chip-pass",
  });
});

test("judge-stability records render unanimity and every attempt", async () => {
  mockApi({ "/api/health": HEALTH, "/api/regressions": LIBRARY });

  renderApp("/regressions");

  expect(await screen.findByText("verdict unanimous")).toHaveClass("chip-pass");
  expect(screen.getByText("first error step 13")).toBeInTheDocument();
  expect(screen.getAllByText("completed")).toHaveLength(2);
  expect(screen.getAllByText("process_integrity")).toHaveLength(2);
});

test("an empty results directory is reported honestly", async () => {
  mockApi({
    "/api/health": HEALTH,
    "/api/regressions": { regression_cards: [], judge_stability: [], unreadable: [] },
  });

  renderApp("/regressions");

  expect(
    await screen.findByText(/No committed validation records found under/),
  ).toBeInTheDocument();
});

test("unreadable committed files are listed, not silently dropped", async () => {
  mockApi({
    "/api/health": HEALTH,
    "/api/regressions": {
      regression_cards: [],
      judge_stability: [],
      unreadable: [{ file: "results/regression/broken.json", reason: "not valid JSON" }],
    },
  });

  renderApp("/regressions");

  const alert = await screen.findByRole("alert");
  expect(within(alert).getByText("results/regression/broken.json")).toBeInTheDocument();
  expect(within(alert).getByText(/not valid JSON/)).toBeInTheDocument();
});
