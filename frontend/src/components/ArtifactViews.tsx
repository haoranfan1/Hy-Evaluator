import type { DeterministicCheck, TaskDetail } from "../api";

export function PatchView({ patch }: { patch: string | null }) {
  if (!patch) {
    return <p className="empty-lane">No verified patch artifact is available.</p>;
  }
  return (
    <pre className="diff" aria-label="Generated patch">
      {patch.split("\n").map((line, index) => {
        let variant = "diff-context";
        if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff --git")) {
          variant = "diff-header";
        } else if (line.startsWith("@@")) {
          variant = "diff-hunk";
        } else if (line.startsWith("+")) {
          variant = "diff-add";
        } else if (line.startsWith("-")) {
          variant = "diff-remove";
        }
        return (
          <span key={index} className={`diff-line ${variant}`}>
            {line || " "}
          </span>
        );
      })}
    </pre>
  );
}

const TEST_CHECK_PREFIXES = ["check-test-fail-to-pass-", "check-test-pass-to-pass-"];

export function VerifierView({
  checks,
  exclusions,
  testOutput,
  runLog,
}: {
  checks: DeterministicCheck[];
  exclusions: string[];
  testOutput: string | null;
  runLog: string | null;
}) {
  const testChecks = checks.filter((check) =>
    TEST_CHECK_PREFIXES.some((prefix) => check.check_id.startsWith(prefix)),
  );
  return (
    <div className="verifier">
      {exclusions.length > 0 && (
        <div className="exclusions" role="note">
          <h4>Excluded from grading</h4>
          <ul>
            {exclusions.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {testChecks.length > 0 ? (
        <table className="test-table">
          <thead>
            <tr>
              <th scope="col">Declared behavioral test</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {testChecks.map((check) => {
              const test = check.evidence.find((reference) => reference.kind === "verifier");
              return (
                <tr key={check.check_id}>
                  <td>
                    <code>{test?.kind === "verifier" ? (test.test_name ?? check.check_id) : check.check_id}</code>
                  </td>
                  <td>
                    <span className={`chip chip-${check.status}`}>
                      {check.status === "unknown" ? "missing" : check.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="empty-lane">No gradeable per-test verifier evidence exists for this run.</p>
      )}

      {testOutput && (
        <details>
          <summary>Raw test output</summary>
          <pre className="log">{testOutput}</pre>
        </details>
      )}
      {runLog && (
        <details>
          <summary>Verifier run log</summary>
          <pre className="log">{runLog}</pre>
        </details>
      )}
    </div>
  );
}

export function TaskView({ task }: { task: TaskDetail }) {
  return (
    <div className="task-view">
      <h4>Problem statement</h4>
      <p className="problem-statement">{task.problem_statement}</p>
      <h4>Behavioral contract</h4>
      <dl className="contract">
        <dt>FAIL_TO_PASS</dt>
        {task.standard_answer.fail_to_pass.map((name) => (
          <dd key={name}>
            <code>{name}</code>
          </dd>
        ))}
        <dt>PASS_TO_PASS</dt>
        {task.standard_answer.pass_to_pass.map((name) => (
          <dd key={name}>
            <code>{name}</code>
          </dd>
        ))}
        <dt>Protected paths</dt>
        {task.protected_paths.map((path) => (
          <dd key={path}>
            <code>{path}</code>
          </dd>
        ))}
      </dl>
    </div>
  );
}
