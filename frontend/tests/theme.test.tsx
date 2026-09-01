import { fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { THEME_STORAGE_KEY } from "../src/App";
import runs from "./fixtures/runs.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

test("the theme defaults to light and toggles to dark", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");
  await screen.findByText("Imported runs");

  expect(document.documentElement.dataset.theme).toBe("light");

  fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  expect(screen.getByRole("button", { name: "Switch to light theme" })).toBeInTheDocument();
});

test("a persisted dark choice applies on the next mount", async () => {
  window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");
  await screen.findByText("Imported runs");

  expect(document.documentElement.dataset.theme).toBe("dark");
});
