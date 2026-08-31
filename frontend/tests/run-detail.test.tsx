import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import inconclusiveDetail from "./fixtures/run-detail-inconclusive.json";
import invalidDetail from "./fixtures/run-detail-invalid.json";
import inconclusiveTrajectory from "./fixtures/trajectory-inconclusive.json";
import invalidTrajectory from "./fixtures/trajectory-invalid.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockInvalidRun() {
  mockApi({
    "/api/health": HEALTH,
    "/api/runs/run-fixture-invalid-first-error/trajectory": invalidTrajectory,
    "/api/runs/run-fixture-invalid-first-error": invalidDetail,
  });
}

test("renders the step timeline in order and marks the first-error step", async () => {
  mockInvalidRun();

  renderApp("/runs/run-fixture-invalid-first-error");

  const banner = await screen.findByRole("note", { name: "First error" });
  expect(banner).toHaveTextContent("First error at step 3");
  expect(banner).toHaveTextContent("call-edit-1");
  expect(banner).toHaveTextContent("task_interpretation");

  const timeline = screen.getByRole("list", { name: "Trajectory steps" });
  const stepLabels = within(timeline)
    .getAllByText(/^Step \d+$/)
    .map((node) => node.textContent);
  expect(stepLabels).toEqual(["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]);

  const stepThree = within(timeline).getByText("Step 3").closest("li");
  expect(stepThree).toHaveClass("step-first-error");
  expect(within(stepThree as HTMLElement).getByText("First error")).toBeInTheDocument();
});

test("selecting a finding highlights every step it cites", async () => {
  mockInvalidRun();

  renderApp("/runs/run-fixture-invalid-first-error");
  await screen.findByRole("note", { name: "First error" });

  const finding = screen.getByTestId("finding-reversed-requirement");
  fireEvent.click(within(finding).getByRole("button", { pressed: false }));

  const timeline = within(screen.getByRole("list", { name: "Trajectory steps" }));
  expect(timeline.getByText("Step 3").closest("li")).toHaveClass("step-cited");
  expect(timeline.getByText("Step 2").closest("li")).not.toHaveClass("step-cited");
});

test("selecting a step marks the findings and checks citing it", async () => {
  mockInvalidRun();

  renderApp("/runs/run-fixture-invalid-first-error");
  await screen.findByRole("note", { name: "First error" });

  const timeline = within(screen.getByRole("list", { name: "Trajectory steps" }));
  fireEvent.click(timeline.getByText("Step 3"));

  const finding = screen.getByTestId("finding-reversed-requirement");
  expect(within(finding).getByText("cites step 3")).toBeInTheDocument();
  expect(finding).toHaveClass("evidence-cites-step");
});

test("the verifier tab shows per-test results and the patch tab shows the diff", async () => {
  mockInvalidRun();

  renderApp("/runs/run-fixture-invalid-first-error");
  await screen.findByRole("note", { name: "First error" });

  fireEvent.click(screen.getByRole("button", { name: "Verifier" }));
  const failedRow = screen
    .getByText("tests/test_normalize.py::test_zero_is_preserved")
    .closest("tr") as HTMLElement;
  expect(within(failedRow).getByText("fail")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Patch" }));
  const diff = screen.getByLabelText("Generated patch");
  expect(diff).toHaveTextContent("return value if value not in (None, 0) else default");
});

test("an inconclusive run surfaces exclusions instead of a verdict", async () => {
  mockApi({
    "/api/health": HEALTH,
    "/api/runs/run-fixture-inconclusive-missing-evidence/trajectory": inconclusiveTrajectory,
    "/api/runs/run-fixture-inconclusive-missing-evidence": inconclusiveDetail,
  });

  renderApp("/runs/run-fixture-inconclusive-missing-evidence");

  expect(await screen.findByText("No process verdict")).toBeInTheDocument();
  expect(screen.queryByRole("note", { name: "First error" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Verifier" }));
  expect(screen.getByText("Excluded from grading")).toBeInTheDocument();
  expect(screen.getByText(/infrastructure failure prevented grading/)).toBeInTheDocument();
});
