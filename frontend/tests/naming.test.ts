import { expect, test } from "vitest";

import { runDisplayName, runShortNames } from "../src/naming";

test("a Harbor trial id becomes repository-number with the suffix kept aside", () => {
  expect(runDisplayName("django__django-16899__yJvk3qg__agent")).toEqual({
    short: "django-16899",
    full: "django__django-16899__yJvk3qg__agent",
    kind: "swebench",
    trial: "yJvk3qg",
  });
});

test("guardrail reruns of the same task keep distinct full ids", () => {
  const baseline = runDisplayName("django__django-16899__yJvk3qg__agent");
  const rerun = runDisplayName("django__django-16899__JbTxrSc__agent");
  expect(baseline.short).toBe(rerun.short);
  expect(baseline.full).not.toBe(rerun.full);
  expect(rerun.trial).toBe("JbTxrSc");
});

test("fixtures and unknown shapes stay readable and never lose the id", () => {
  expect(runDisplayName("run-fixture-invalid-first-error")).toEqual({
    short: "run-fixture-invalid-first-error",
    full: "run-fixture-invalid-first-error",
    kind: "fixture",
    trial: null,
  });
  expect(runDisplayName("something-else").short).toBe("something-else");
});

test("a list disambiguates same-task runs with their trial suffix", () => {
  const names = runShortNames([
    "django__django-16899__yJvk3qg__agent",
    "django__django-16899__JbTxrSc__agent",
    "django__django-14017__n7sw8mU__agent",
    "run-fixture-valid",
  ]);
  expect(names.get("django__django-16899__yJvk3qg__agent")).toBe("django-16899 · yJvk3qg");
  expect(names.get("django__django-16899__JbTxrSc__agent")).toBe("django-16899 · JbTxrSc");
  expect(names.get("django__django-14017__n7sw8mU__agent")).toBe("django-14017");
  expect(names.get("run-fixture-valid")).toBe("run-fixture-valid");
});
