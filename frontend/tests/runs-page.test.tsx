import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import runs from "./fixtures/runs.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

test("lists every imported run with outcome, process, and first error", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");

  const table = within(await screen.findByRole("table"));
  expect(table.getByText("run-fixture-valid")).toBeInTheDocument();
  expect(table.getByText("run-fixture-invalid-first-error")).toBeInTheDocument();
  expect(table.getByText("run-fixture-inconclusive-missing-evidence")).toBeInTheDocument();

  expect(table.getByText("resolved")).toBeInTheDocument();
  expect(table.getByText("unresolved")).toBeInTheDocument();
  expect(table.getByText("step 3 · task_interpretation")).toBeInTheDocument();
  expect(table.getAllByText("easy").length).toBeGreaterThan(0);
});

test("filters the list by process status on the client", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");
  await screen.findByText("run-fixture-valid");

  fireEvent.change(screen.getByLabelText("Process"), { target: { value: "invalid" } });

  expect(screen.getByText("run-fixture-invalid-first-error")).toBeInTheDocument();
  expect(screen.queryByText("run-fixture-valid")).not.toBeInTheDocument();
  expect(screen.queryByText("run-fixture-inconclusive-missing-evidence")).not.toBeInTheDocument();
});

test("real runs show a short name; the exact id lives in the tooltip and link", async () => {
  const base = { ...runs.runs[0], task_id: "django__django-16899", repository: "django/django" };
  const baseline = { ...base, run_id: "django__django-16899__yJvk3qg__agent" };
  const rerun = { ...base, run_id: "django__django-16899__JbTxrSc__agent" };
  const other = { ...base, run_id: "django__django-14017__n7sw8mU__agent" };
  mockApi({ "/api/health": HEALTH, "/api/runs": { runs: [baseline, rerun, other] } });

  renderApp("/runs");

  const single = await screen.findByRole("link", { name: "django-14017" });
  expect(single).toHaveAttribute("href", "/runs/django__django-14017__n7sw8mU__agent");
  expect(single).toHaveAttribute("title", "django__django-14017__n7sw8mU__agent");
  // Same task twice: the trial suffix comes back so the rows stay distinguishable.
  expect(screen.getByRole("link", { name: "django-16899 · yJvk3qg" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "django-16899 · JbTxrSc" })).toBeInTheDocument();
  expect(screen.queryByText("django/django")).not.toBeInTheDocument();
  expect(screen.getByText("Process (evaluator)")).toBeInTheDocument();
  expect(screen.getByText("Reviews (human)")).toBeInTheDocument();
});
