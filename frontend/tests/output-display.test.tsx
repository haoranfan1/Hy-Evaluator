import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import type { DeterministicCheck } from "../src/api";
import { VerifierView } from "../src/components/ArtifactViews";
import { ClampedText, CommandBlock, ObservationBlock } from "../src/components/OutputBlock";
import { StepTimeline } from "../src/components/StepTimeline";

function longOutput(lines: number): string {
  return Array.from({ length: lines }, (_, index) => `line-${index + 1}`).join("\n");
}

test("a structured observation renders an exit chip and clean output", () => {
  render(
    <ObservationBlock
      content={JSON.stringify({ returncode: 0, output: "collected 3 items\n3 passed" })}
    />,
  );

  const observation = screen.getByLabelText("Observation");
  expect(within(observation).getByText("exit 0")).toHaveClass("chip-pass");
  const body = within(observation).getByLabelText("Observation output");
  expect(body.textContent).toBe("collected 3 items\n3 passed");
  expect(observation.textContent).not.toContain("returncode");
  expect(observation.textContent).not.toContain("\\n");
});

test("a failing exit code renders a fail chip", () => {
  render(<ObservationBlock content={JSON.stringify({ returncode: 2, output: "boom" })} />);

  expect(screen.getByText("exit 2")).toHaveClass("chip-fail");
});

test("an empty structured output says so instead of rendering a blank block", () => {
  render(<ObservationBlock content={JSON.stringify({ returncode: 0, output: "" })} />);

  expect(screen.getByText("no output")).toBeInTheDocument();
  expect(screen.queryByLabelText("Observation output")).not.toBeInTheDocument();
});

test("long observation output collapses to a head/tail preview and expands verbatim", () => {
  const output = longOutput(40);
  render(<ObservationBlock content={JSON.stringify({ returncode: 1, output })} />);

  const observation = screen.getByLabelText("Observation");
  expect(observation.textContent).toContain("line-1");
  expect(observation.textContent).toContain("line-40");
  expect(observation.textContent).not.toContain("line-20");

  const toggle = screen.getByRole("button", { name: /Show 28 hidden lines/ });
  fireEvent.click(toggle);
  expect(screen.getByLabelText("Observation output").textContent).toContain("line-20");

  fireEvent.click(screen.getByRole("button", { name: "Collapse to preview" }));
  expect(screen.getByLabelText("Observation").textContent).not.toContain("line-20");
});

test("short unstructured observations render fully without a toggle", () => {
  render(<ObservationBlock content="Patch applied." />);

  expect(screen.getByLabelText("Observation output").textContent).toBe("Patch applied.");
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

test("a bash command renders as real lines, not JSON escapes", () => {
  render(
    <CommandBlock
      args={{ command: "cd /testbed/tests; python - <<'EOF'\npath = \"schema/tests.py\"\nEOF" }}
    />,
  );

  const command = screen.getByLabelText("Command");
  expect(command.textContent).toContain('path = "schema/tests.py"');
  expect(command.textContent).not.toContain("{");
  expect(command.textContent).not.toContain("\\n");
});

test("non-command tool arguments keep a readable JSON rendering", () => {
  render(<CommandBlock args={{ patch: "return value" }} />);

  expect(screen.getByLabelText("Tool arguments").textContent).toContain('"patch"');
});

function testCheck(id: string, status: DeterministicCheck["status"]): DeterministicCheck {
  return {
    check_id: id,
    status,
    summary: `check ${id} is ${status}`,
    evidence: [{ kind: "verifier", artifact_id: "artifact-x", test_name: `tests/${id}` }],
    hard_process_failure: false,
  };
}

test("a large all-passing test table collapses to a counted summary", () => {
  const checks = [
    testCheck("check-test-fail-to-pass-1", "fail"),
    ...Array.from({ length: 12 }, (_, index) =>
      testCheck(`check-test-pass-to-pass-${index + 1}`, "pass"),
    ),
  ];
  render(<VerifierView checks={checks} exclusions={[]} testOutput={null} runLog={null} />);

  // The failing row stays visible outside the collapsed section.
  const failedRow = screen.getByText("tests/check-test-fail-to-pass-1").closest("tr");
  expect(failedRow).not.toBeNull();
  expect(screen.getByText(/12\/12 declared remaining tests passed/)).toBeInTheDocument();
  expect(screen.queryByText("tests/check-test-pass-to-pass-5")).not.toBeVisible();
});

test("a small test table renders in full with no collapsing", () => {
  const checks = [
    testCheck("check-test-fail-to-pass-1", "pass"),
    testCheck("check-test-pass-to-pass-1", "pass"),
  ];
  render(<VerifierView checks={checks} exclusions={[]} testOutput={null} runLog={null} />);

  expect(screen.getByText("tests/check-test-pass-to-pass-1")).toBeVisible();
  expect(screen.queryByText(/declared/)).not.toBeInTheDocument();
});

test("observations with a null source_call_id still render on the step", () => {
  // Harbor's chat-completions conversion leaves source_call_id null on every
  // real run; the timeline must attach those results to the step instead of
  // silently dropping them.
  const step = {
    step_id: 13,
    source: "agent" as const,
    message: "edit the test expectations",
    tool_calls: [
      {
        tool_call_id: "chatcmpl-tool-1",
        function_name: "bash",
        arguments: { command: "sed -i 's/a/b/' tests/x.py" },
      },
    ],
    observation: {
      results: [
        {
          source_call_id: null,
          content: JSON.stringify({ returncode: 0, output: "done" }),
        },
      ],
    },
  };
  render(
    <StepTimeline
      steps={[step]}
      firstError={null}
      highlightedSteps={new Set()}
      selectedStep={null}
      onSelectStep={() => {}}
    />,
  );

  const observation = screen.getByLabelText("Observation");
  expect(within(observation).getByText("exit 0")).toBeInTheDocument();
  expect(within(observation).getByLabelText("Observation output").textContent).toBe("done");
});

test("long prose summaries clamp with an explicit toggle", () => {
  const text = `The patch modifies protected paths; ${"step 9 tool call 'chatcmpl-tool-x' references 'tests/admin_checks/tests.py'; ".repeat(12)}`;
  render(<ClampedText className="evidence-summary" text={text} />);

  expect(screen.getByText(/…/)).toBeInTheDocument();
  const toggle = screen.getByRole("button", { name: /show all/ });
  fireEvent.click(toggle);
  expect(screen.getByRole("button", { name: "show less" })).toBeInTheDocument();
});

test("short summaries render without a toggle", () => {
  render(<ClampedText className="evidence-summary" text="No manifest-protected path is accessed." />);

  expect(screen.getByText("No manifest-protected path is accessed.")).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
