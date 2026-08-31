// Record the ≤2-minute workbench demo as one continuous browser session.
//
// Preconditions (see docs/DEMO.md for the full re-recording procedure):
//   - The API serves the DEMO COPY of the workbench state on 127.0.0.1:8000
//     (WORKBENCH_DATA_DIR=.local/workbench-demo) so the one on-camera write —
//     a blinded label on the synthetic fixture run — never touches the frozen
//     validated evidence.
//   - The Vite dev server runs on 127.0.0.1:5173.
//   - In the copy, run-fixture-invalid-first-error has zero reviews (blinded),
//     and the real slice runs keep their recorded labels and adjudications.
//
// Run from frontend/:  node scripts/record_demo.mjs [output-dir]
import { chromium } from "@playwright/test";

const OUT = process.argv[2] ?? "demo-recording";
const UI = "http://localhost:5173";
const FIXTURE = "run-fixture-invalid-first-error";
const REAL = "django__django-16899__yJvk3qg__agent";
const REPORT_URL =
  "https://github.com/haoranfan1/Hy-Evaluator/blob/main/docs/REPORT.md";

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 720 } },
});
const page = await context.newPage();
const beat = (ms) => page.waitForTimeout(ms);
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` });

// Scene 1 — the run list: real SWE-bench runs and synthetic fixtures together.
await page.goto(`${UI}/runs`, { waitUntil: "networkidle" });
await page.waitForSelector(`text=${REAL}`);
await beat(6500);
await shot("s1-run-list");

// Scene 2 — the blinded human workflow on the unresolved fixture run:
// evidence visible, verdict hidden, label saved, verdict revealed in agreement.
await page.goto(`${UI}/runs/${FIXTURE}`, { waitUntil: "networkidle" });
await page.waitForSelector('section[aria-label="Blinded initial review"]');
await beat(3000);
await page.getByLabel("Reviewer alias").fill("operator-demo-day10");
await beat(700);
await page.locator('label:has-text("Process status") select').selectOption("invalid");
await beat(700);
await page.locator('label:has-text("First error") select').selectOption("located");
await beat(700);
await page.getByLabel("Step ID").fill("3");
await beat(700);
await page
  .locator('label:has-text("Primary category") select')
  .selectOption("task_interpretation");
await beat(700);
await page
  .getByLabel("Label notes")
  .fill("Step 3 first contradicts the explicit requirement to preserve zero.");
await beat(2000);
await shot("s2-blinded-form");
const saved = page.waitForResponse(
  (response) => response.url().includes("/initial-review") && response.status() === 201,
);
await page.getByRole("button", { name: "Save initial label and reveal the verdict" }).click();
await saved;
await page.waitForSelector('[aria-label="First error"]');
await beat(4000);
await shot("s2-revealed");
await page.locator("li.step-first-error").first().scrollIntoViewIfNeeded();
await beat(4000);
await shot("s2-first-error-step");

// Scene 3 — the flagship real case: django-16899, resolved by the official
// verifier, human-labeled invalid at step 13 (rewriting the graded
// assertions); the stored v1 evaluation anchored at step 9 — the measured
// gap the regression card in the final scene shows fixed by v2.
await page.goto(`${UI}/runs/${REAL}`, { waitUntil: "networkidle" });
await page.waitForSelector('[aria-label="First error"]');
await beat(3500);
await shot("s3-banner");
const step13 = page
  .locator("li")
  .filter({ has: page.locator(".step-id", { hasText: /^Step 13$/ }) })
  .first();
await step13.scrollIntoViewIfNeeded();
await step13.locator("button.step-select").click();
await beat(4500);
await shot("s3-step13");
await page.locator('section[aria-label="Review history"]').scrollIntoViewIfNeeded();
await beat(4500);
await shot("s3-reviews");

// Scene 4 — validated slice analytics: every number with provenance,
// the difficulty inversion, and the adjudication-annotated case links.
await page.goto(`${UI}/analytics?scope=day8-slice-v1`, { waitUntil: "networkidle" });
await page.waitForSelector("text=Scope:");
await beat(4000);
await shot("s4-analytics-top");
await page.locator("h3", { hasText: "Required metrics" }).scrollIntoViewIfNeeded();
await beat(4500);
await shot("s4-metrics");
await page
  .locator('section[aria-label="Representative cases"]')
  .scrollIntoViewIfNeeded();
await beat(5000);
await shot("s4-cases");

// Scene 5 — the published report: the evaluator v2 regression card measured
// against the frozen human labels.
await page.goto(REPORT_URL, { waitUntil: "domcontentloaded" });
await page.waitForSelector("text=False positives on human-valid runs", {
  timeout: 30000,
});
await page
  .locator("text=False positives on human-valid runs")
  .first()
  .scrollIntoViewIfNeeded();
await beat(6500);
await shot("s5-report-regression");

await page.close();
await context.close();
await browser.close();
console.log(`demo recorded into ${OUT}/ (video .webm plus scene screenshots)`);
