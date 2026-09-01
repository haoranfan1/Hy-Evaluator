import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";

import { fetchAnalytics } from "../api";

function formatRate(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(0)}%`;
}

function formatCount(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

const OUTCOME_ORDER = ["resolved", "unresolved", "inconclusive", "not_evaluated"];
const PROCESS_ORDER = ["valid", "invalid", "inconclusive", "not_evaluated"];

export function AnalyticsPage() {
  const [searchParams] = useSearchParams();
  const scope = searchParams.get("scope") ?? undefined;
  const analytics = useQuery({
    queryKey: ["analytics", scope ?? "all"],
    queryFn: () => fetchAnalytics(scope),
    retry: false,
  });

  if (analytics.isPending) {
    return <p>Computing analytics…</p>;
  }
  if (analytics.isError || !analytics.data) {
    return <p role="alert">Analytics could not be loaded from the local API.</p>;
  }
  const summary = analytics.data;
  const quadrantCell = (outcome: string, process: string) =>
    summary.quadrant.find(
      (cell) => cell.outcome_status === outcome && cell.process_status === process,
    );
  const outcomes = OUTCOME_ORDER.filter((outcome) =>
    summary.quadrant.some((cell) => cell.outcome_status === outcome),
  );
  const processes = PROCESS_ORDER.filter((process) =>
    summary.quadrant.some((cell) => cell.process_status === process),
  );
  const maxCategoryCount = Math.max(
    1,
    ...summary.primary_error_distribution.map((entry) => entry.count),
  );

  return (
    <section>
      <header className="page-head">
        <div>
          <h2>Aggregate analytics</h2>
          <p className="page-lede">
            {summary.run_count} runs · {summary.evaluated_count} evaluated ·{" "}
            {summary.reviewed_count} reviewed · {summary.adjudicated_count} adjudicated. Every
            number carries its provenance: <span className="chip chip-human">human</span>{" "}
            <span className="chip chip-evaluator">evaluator</span>{" "}
            <span className="chip chip-mixed">mixed</span>{" "}
            <span className="chip chip-official">official</span>
          </p>
          {scope ? (
            <p className="page-lede">
              Scope: <span className="chip chip-official">{scope}</span> — frozen evaluation
              slice with {summary.configuration.scope_task_count} tasks
              {summary.configuration.scope_tasks_without_runs !== "none"
                ? ` (no runs yet: ${summary.configuration.scope_tasks_without_runs})`
                : ""}
              . <Link to="/analytics">View all runs</Link>
            </p>
          ) : null}
        </div>
      </header>

      <div className="analytics-grid">
        <section className="analytics-card" aria-label="Outcome versus process">
          <h3>Outcome × process</h3>
          <table className="quadrant-table">
            <thead>
              <tr>
                <th scope="col">outcome \ process</th>
                {processes.map((process) => (
                  <th scope="col" key={process}>
                    {process.replace("_", " ")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {outcomes.map((outcome) => (
                <tr key={outcome}>
                  <th scope="row">{outcome.replace("_", " ")}</th>
                  {processes.map((process) => {
                    const cell = quadrantCell(outcome, process);
                    return (
                      <td key={process} className={cell ? "quadrant-filled" : ""}>
                        {cell ? (
                          <>
                            <span className="quadrant-count">{cell.run_ids.length}</span>
                            {cell.run_ids.map((runId) => (
                              <Link className="quadrant-link" key={runId} to={`/runs/${runId}`}>
                                {runId.replace("run-fixture-", "")}
                              </Link>
                            ))}
                          </>
                        ) : (
                          <span className="quadrant-count quadrant-zero">0</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="analytics-card" aria-label="Primary error distribution">
          <h3>Primary error distribution</h3>
          {summary.primary_error_distribution.length === 0 && (
            <p className="empty-lane">No invalid processes yet.</p>
          )}
          {summary.primary_error_distribution.map((entry) => (
            <div className="bar-row" key={entry.category}>
              <span className="bar-label">{entry.category}</span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{ width: `${(entry.count / maxCategoryCount) * 100}%` }}
                />
              </span>
              <span className="bar-count">
                {entry.count}
                <span className="bar-provenance">
                  {entry.human_count > 0 && ` · ${entry.human_count} human`}
                  {entry.evaluator_count > 0 && ` · ${entry.evaluator_count} evaluator`}
                </span>
              </span>
            </div>
          ))}
        </section>
      </div>

      <section className="analytics-card" aria-label="Required metrics">
        <h3>Required metrics</h3>
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">Metric</th>
              <th scope="col">Value</th>
              <th scope="col">n / d</th>
              <th scope="col">Provenance</th>
              <th scope="col">Exclusions</th>
            </tr>
          </thead>
          <tbody>
            {summary.metrics.map((entry) => (
              <tr key={entry.metric_id}>
                <td>
                  <code className="metric-id">{entry.metric_id}</code>
                  <p className="metric-definition">{entry.definition}</p>
                </td>
                <td>{formatRate(entry.value)}</td>
                <td>
                  {entry.numerator} / {entry.denominator}
                </td>
                <td>
                  <span className={`chip chip-${entry.provenance}`}>{entry.provenance}</span>
                </td>
                <td>
                  {entry.exclusions.length === 0 ? (
                    "—"
                  ) : (
                    <details>
                      <summary>{entry.exclusions.length} excluded</summary>
                      <ul className="exclusion-list">
                        {entry.exclusions.map((reason, index) => (
                          <li key={index}>{reason}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="analytics-card" aria-label="Results by difficulty">
        <h3>Results by official difficulty</h3>
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">Difficulty</th>
              <th scope="col">Runs</th>
              <th scope="col">Resolved</th>
              <th scope="col">Outcome rate</th>
              <th scope="col">Process valid</th>
              <th scope="col">Process rate</th>
              <th scope="col">Inconclusive</th>
              <th scope="col">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {summary.difficulty_table.map((row) => (
              <tr key={row.label}>
                <td>{row.label}</td>
                <td>{row.total_runs}</td>
                <td>
                  {row.resolved_runs} / {row.gradeable_runs}
                </td>
                <td>{formatRate(row.outcome_rate)}</td>
                <td>
                  {row.process_valid_runs} / {row.process_gradeable_runs}
                </td>
                <td>{formatRate(row.process_valid_rate)}</td>
                <td>{row.inconclusive_runs}</td>
                <td>
                  <span className={`chip chip-${row.provenance}`}>{row.provenance}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="decline-note">
          Observed decline interval: <strong>{summary.observed_decline_interval}</strong> ·
          statistically supported:{" "}
          <strong>{summary.statistically_supported_decline_interval}</strong> (bootstrap seed{" "}
          {summary.configuration.bootstrap_seed}, {summary.configuration.bootstrap_resamples}{" "}
          resamples)
        </p>
      </section>

      <section className="analytics-card" aria-label="Agent effort">
        <h3>Agent effort by difficulty × outcome</h3>
        <p className="record-meta">
          Steps and tool calls counted from the stored ATIF trajectories; a run whose trajectory
          cannot be read is reported as missing, never interpolated.
        </p>
        {summary.efficiency.length === 0 && <p className="empty-lane">No runs yet.</p>}
        {summary.efficiency.length > 0 && (
          <table className="run-table">
            <thead>
              <tr>
                <th scope="col">Difficulty</th>
                <th scope="col">Outcome</th>
                <th scope="col">Runs</th>
                <th scope="col">Median steps</th>
                <th scope="col">Steps range</th>
                <th scope="col">Median tool calls</th>
                <th scope="col">Provenance</th>
              </tr>
            </thead>
            <tbody>
              {summary.efficiency.map((row) => (
                <tr key={`${row.difficulty}-${row.outcome}`}>
                  <td>{row.difficulty}</td>
                  <td>{row.outcome.replaceAll("_", " ")}</td>
                  <td>
                    {row.run_count}
                    {row.runs_with_trajectory < row.run_count &&
                      ` (${row.run_count - row.runs_with_trajectory} without trajectory)`}
                  </td>
                  <td>{formatCount(row.median_steps)}</td>
                  <td>
                    {row.min_steps === null || row.max_steps === null
                      ? "—"
                      : row.min_steps === row.max_steps
                        ? row.min_steps
                        : `${row.min_steps}–${row.max_steps}`}
                  </td>
                  <td>{formatCount(row.median_tool_calls)}</td>
                  <td>
                    <span className={`chip chip-${row.provenance}`}>{row.provenance}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="analytics-grid">
        <section className="analytics-card" aria-label="Excluded runs">
          <h3>Excluded / inconclusive runs</h3>
          {summary.excluded_runs.length === 0 && <p className="empty-lane">None.</p>}
          <ul className="exclusion-list">
            {summary.excluded_runs.map((entry) => (
              <li key={entry.run_id}>
                <Link to={`/runs/${entry.run_id}`}>{entry.run_id}</Link>
                <br />
                {entry.reasons.join("; ")}
              </li>
            ))}
          </ul>
        </section>

        <section className="analytics-card" aria-label="Representative cases">
          <h3>Representative cases</h3>
          {summary.cases.length === 0 && <p className="empty-lane">None yet.</p>}
          <ul className="case-list">
            {summary.cases.map((entry) => (
              <li key={`${entry.run_id}-${entry.kind}`}>
                <Link to={`/runs/${entry.run_id}`}>{entry.run_id}</Link>
                <span className="chip chip-category">{entry.kind.replaceAll("_", " ")}</span>
                {entry.adjudication && (
                  <span
                    className={`chip ${
                      entry.adjudication === "reject" ? "chip-reject" : "chip-accept"
                    }`}
                  >
                    {entry.adjudication === "reject"
                      ? "rejected: false positive"
                      : `human ${entry.adjudication}`}
                  </span>
                )}
                <br />
                {entry.note}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
