import { screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import runs from "./fixtures/runs.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows the API health state in the header", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");

  expect(await screen.findByText("API degraded · v0.1.0")).toBeInTheDocument();
  expect(screen.getByText("Evidence debugger")).toBeInTheDocument();
});

test("the root path redirects to the run list", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/");

  expect(await screen.findByText("Imported runs")).toBeInTheDocument();
});
