import { fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { LANGUAGE_STORAGE_KEY, MESSAGES } from "../src/i18n";
import runs from "./fixtures/runs.json";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

test("the UI defaults to English", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");

  expect(await screen.findByText("Imported runs")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "EN" })).toHaveAttribute("aria-pressed", "true");
});

test("the toggle switches chrome to Chinese and persists the choice", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");
  await screen.findByText("Imported runs");

  fireEvent.click(screen.getByRole("button", { name: "中文" }));

  expect(screen.getByText("已导入的运行")).toBeInTheDocument();
  expect(screen.getByText("运行", { selector: "a" })).toBeInTheDocument();
  expect(screen.getByText("回归")).toBeInTheDocument();
  expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("zh");
});

test("evidence content stays untranslated when chrome is Chinese", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");
  const runId = runs.runs[0].run_id;
  expect(await screen.findByText(runId)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "中文" }));

  // Run ids, statuses, and categories are data, not chrome.
  expect(screen.getByText(runId)).toBeInTheDocument();
  expect(screen.getAllByText(runs.runs[0].outcome_status as string).length).toBeGreaterThan(0);
});

test("a persisted choice applies on the next mount", async () => {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
  mockApi({ "/api/health": HEALTH, "/api/runs": runs });

  renderApp("/runs");

  expect(await screen.findByText("已导入的运行")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "中文" })).toHaveAttribute("aria-pressed", "true");
});

test("every message provides both languages and balanced placeholders", () => {
  for (const [key, entry] of Object.entries(MESSAGES)) {
    expect(entry.en.length, key).toBeGreaterThan(0);
    expect(entry.zh.length, key).toBeGreaterThan(0);
    const placeholders = (text: string) => [...text.matchAll(/\{[a-zA-Z]+\}/g)].map((m) => m[0]);
    expect(placeholders(entry.zh).sort(), key).toEqual(placeholders(entry.en).sort());
  }
});
