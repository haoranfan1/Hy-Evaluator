import type { DeterministicCheck, TaskDetail } from "../api";
import { useI18n } from "../i18n";

export function PatchView({ patch }: { patch: string | null }) {
  const { t } = useI18n();
  if (!patch) {
    return <p className="empty-lane">{t("patch.empty")}</p>;
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

// Above this count, an all-passing test table collapses to a summary line —
// dozens of green rows are noise during review, while any non-pass row always
// stays visible.
const PASSED_TABLE_COLLAPSE_THRESHOLD = 10;

function TestTable({ checks }: { checks: DeterministicCheck[] }) {
  const { t } = useI18n();
  return (
    <table className="test-table">
      <thead>
        <tr>
          <th scope="col">{t("verifier.testCol")}</th>
          <th scope="col">{t("verifier.resultCol")}</th>
        </tr>
      </thead>
      <tbody>
        {checks.map((check) => {
          const test = check.evidence.find((reference) => reference.kind === "verifier");
          return (
            <tr key={check.check_id}>
              <td>
                <code>
                  {test?.kind === "verifier" ? (test.test_name ?? check.check_id) : check.check_id}
                </code>
              </td>
              <td>
                <span className={`chip chip-${check.status}`}>
                  {check.status === "unknown" ? t("verifier.missing") : check.status}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

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
  const { t } = useI18n();
  const testChecks = checks.filter((check) =>
    TEST_CHECK_PREFIXES.some((prefix) => check.check_id.startsWith(prefix)),
  );
  const attention = testChecks.filter((check) => check.status !== "pass");
  const passed = testChecks.filter((check) => check.status === "pass");
  const collapsePassed = passed.length > PASSED_TABLE_COLLAPSE_THRESHOLD;
  return (
    <div className="verifier">
      {exclusions.length > 0 && (
        <div className="exclusions" role="note">
          <h4>{t("verifier.excluded")}</h4>
          <ul>
            {exclusions.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {testChecks.length === 0 && <p className="empty-lane">{t("verifier.empty")}</p>}
      {testChecks.length > 0 && !collapsePassed && <TestTable checks={testChecks} />}
      {collapsePassed && (
        <>
          {attention.length > 0 && <TestTable checks={attention} />}
          <details className="passed-tests">
            <summary>
              <span className="chip chip-pass">pass</span>{" "}
              {t(attention.length > 0 ? "verifier.passedRemaining" : "verifier.passedAll", {
                n: passed.length,
                d: passed.length,
              })}
            </summary>
            <TestTable checks={passed} />
          </details>
        </>
      )}

      {testOutput && (
        <details>
          <summary>{t("verifier.rawOutput")}</summary>
          <pre className="log">{testOutput}</pre>
        </details>
      )}
      {runLog && (
        <details>
          <summary>{t("verifier.runLog")}</summary>
          <pre className="log">{runLog}</pre>
        </details>
      )}
    </div>
  );
}

export function TaskView({ task }: { task: TaskDetail }) {
  const { t } = useI18n();
  return (
    <div className="task-view">
      <h4>{t("task.problem")}</h4>
      <p className="problem-statement">{task.problem_statement}</p>
      <h4>{t("task.contract")}</h4>
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
        <dt>{t("task.protectedPaths")}</dt>
        {task.protected_paths.map((path) => (
          <dd key={path}>
            <code>{path}</code>
          </dd>
        ))}
      </dl>
    </div>
  );
}
