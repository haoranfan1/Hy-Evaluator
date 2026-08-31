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
