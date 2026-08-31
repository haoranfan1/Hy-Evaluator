import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import analytics from "./fixtures/analytics.json";
import blindedDetail from "./fixtures/run-detail-invalid.json";
import adjudicatedDetail from "./fixtures/run-detail-invalid-adjudicated.json";
import initialReviewDetail from "./fixtures/run-detail-invalid-initial-review.json";
import invalidTrajectory from "./fixtures/trajectory-invalid.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

const DETAIL_ROUTES = {
  "/api/health": HEALTH,
  "/api/runs/run-fixture-invalid-first-error/trajectory": invalidTrajectory,
};

test("an unreviewed run hides the verdict and asks for the blinded label", async () => {
  mockApi({
    ...DETAIL_ROUTES,
    "/api/runs/run-fixture-invalid-first-error": blindedDetail,
  });

  renderApp("/runs/run-fixture-invalid-first-error");

  expect(await screen.findByRole("region", { name: "Blinded initial review" })).toBeInTheDocument();
  expect(screen.getByText("process: hidden until your initial label")).toBeInTheDocument();
  expect(screen.queryByRole("note", { name: "First error" })).not.toBeInTheDocument();
  expect(screen.queryByTestId("finding-reversed-requirement")).not.toBeInTheDocument();
  expect(
    screen.getByText("Semantic findings are hidden until your blinded initial label is saved."),
  ).toBeInTheDocument();
  // Deterministic evidence stays visible for the reviewer.
  expect(screen.getByText("outcome: unresolved")).toBeInTheDocument();
  expect(screen.getByTestId("check-identity")).toBeInTheDocument();
});

test("saving the blinded label posts the initial review", async () => {
  const calls = mockApi({
    ...DETAIL_ROUTES,
    "/api/runs/run-fixture-invalid-first-error": blindedDetail,
  });

  renderApp("/runs/run-fixture-invalid-first-error");
  await screen.findByRole("region", { name: "Blinded initial review" });

  fireEvent.change(screen.getByLabelText("Step ID"), { target: { value: "3" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Save initial label and reveal the verdict" }),
  );

  await waitFor(() => {
    expect(
      calls.some(
        (call) =>
          call.method === "POST" &&
          call.url.endsWith(
            "/api/evaluations/evaluation-run-fixture-invalid-first-error/initial-review",
          ),
      ),
    ).toBe(true);
  });
  const posted = calls.find((call) => call.method === "POST");
  const body = posted?.body as {
    initial_label: { process_status: string; first_error_step_id: number };
  };
  expect(body.initial_label.process_status).toBe("invalid");
  expect(body.initial_label.first_error_step_id).toBe(3);
});

test("after the initial review the verdict is revealed and adjudication is offered", async () => {
  mockApi({
    ...DETAIL_ROUTES,
    "/api/runs/run-fixture-invalid-first-error": initialReviewDetail,
  });

  renderApp("/runs/run-fixture-invalid-first-error");

  expect(await screen.findByRole("note", { name: "First error" })).toBeInTheDocument();
  expect(screen.getByTestId("finding-reversed-requirement")).toBeInTheDocument();
  const adjudicationPanel = screen.getByRole("region", { name: "Adjudication" });
  expect(adjudicationPanel).toHaveTextContent("Blinded initial label: invalid");
  expect(screen.getByRole("button", { name: "Append adjudication" })).toBeInTheDocument();
});

test("an adjudicated run shows the immutable review history", async () => {
  mockApi({
    ...DETAIL_ROUTES,
    "/api/runs/run-fixture-invalid-first-error": adjudicatedDetail,
  });

  renderApp("/runs/run-fixture-invalid-first-error");

  const history = await screen.findByRole("region", { name: "Review history" });
  expect(history).toHaveTextContent("v1");
  expect(history).toHaveTextContent("v2");
  expect(history).toHaveTextContent("accept");
  expect(
    screen.queryByRole("button", { name: "Append adjudication" }),
  ).not.toBeInTheDocument();
});

test("the analytics page renders every required metric with provenance", async () => {
  mockApi({ "/api/health": HEALTH, "/api/analytics/summary": analytics });

  renderApp("/analytics");

  expect(await screen.findByText("final_answer_accuracy")).toBeInTheDocument();
  expect(screen.getByText("exact_first_error_localization_accuracy")).toBeInTheDocument();
  expect(screen.getByText("correct_result_evaluator_false_positive_rate")).toBeInTheDocument();

  const difficulty = screen.getByRole("region", { name: "Results by difficulty" });
  expect(difficulty).toHaveTextContent("easy");
  expect(difficulty).toHaveTextContent("1 / 2");
  expect(difficulty).toHaveTextContent("not_established");

  const excluded = screen.getByRole("region", { name: "Excluded runs" });
  expect(excluded).toHaveTextContent("run-fixture-inconclusive-missing-evidence");

  const quadrant = screen.getByRole("region", { name: "Outcome versus process" });
  expect(quadrant).toHaveTextContent("resolved");
  expect(quadrant).toHaveTextContent("invalid");
});
