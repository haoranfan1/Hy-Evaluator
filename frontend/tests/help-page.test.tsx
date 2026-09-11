import { fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { HELP_SECTIONS } from "../src/help-content";
import { HEALTH, mockApi, renderApp } from "./helpers";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

test("the guide renders every section in English and switches to Chinese", async () => {
  mockApi({ "/api/health": HEALTH });

  renderApp("/help");

  expect(await screen.findByRole("heading", { name: "Guide" })).toBeInTheDocument();
  for (const section of HELP_SECTIONS) {
    expect(screen.getByRole("heading", { name: section.title.en })).toBeInTheDocument();
  }
  expect(screen.getByText("process_integrity")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "中文" }));

  expect(screen.getByRole("heading", { name: "使用指南" })).toBeInTheDocument();
  for (const section of HELP_SECTIONS) {
    expect(screen.getByRole("heading", { name: section.title.zh })).toBeInTheDocument();
  }
  // Identifiers stay literal in both languages.
  expect(screen.getByText("process_integrity")).toBeInTheDocument();
});

test("the guide is reachable from the header navigation", async () => {
  mockApi({ "/api/health": HEALTH, "/api/runs": { runs: [] } });

  renderApp("/runs");
  await screen.findByText("Imported runs");

  fireEvent.click(screen.getByRole("link", { name: "Guide" }));

  expect(await screen.findByRole("heading", { name: "Guide" })).toBeInTheDocument();
});

test("every guide section is complete in both languages", () => {
  const ids = new Set<string>();
  for (const section of HELP_SECTIONS) {
    expect(ids.has(section.id), section.id).toBe(false);
    ids.add(section.id);
    expect(section.title.en.length, section.id).toBeGreaterThan(0);
    expect(section.title.zh.length, section.id).toBeGreaterThan(0);
    expect(section.paragraphs.en.length, section.id).toBe(section.paragraphs.zh.length);
    expect(section.paragraphs.en.length, section.id).toBeGreaterThan(0);
    for (const term of section.terms ?? []) {
      expect(term.en.length, term.term).toBeGreaterThan(0);
      expect(term.zh.length, term.term).toBeGreaterThan(0);
    }
  }
});
