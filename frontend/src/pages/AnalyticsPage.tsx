import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";

import { fetchAnalytics } from "../api";
import { useI18n } from "../i18n";

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
  const { t } = useI18n();
  const [searchParams] = useSearchParams();
  const scope = searchParams.get("scope") ?? undefined;
  const analytics = useQuery({
    queryKey: ["analytics", scope ?? "all"],
    queryFn: () => fetchAnalytics(scope),
    retry: false,
  });

  if (analytics.isPending) {
    return <p>{t("analytics.loading")}</p>;
  }
  if (analytics.isError || !analytics.data) {
    return <p role="alert">{t("analytics.error")}</p>;
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
          <h2>{t("analytics.title")}</h2>
          <p className="page-lede">
            {t("analytics.lede", {
              runs: summary.run_count,
              evaluated: summary.evaluated_count,
              reviewed: summary.reviewed_count,
              adjudicated: summary.adjudicated_count,
            })}{" "}
            <span className="chip chip-human">human</span>{" "}
            <span className="chip chip-evaluator">evaluator</span>{" "}
            <span className="chip chip-mixed">mixed</span>{" "}
            <span className="chip chip-official">official</span>
          </p>
          {scope ? (
            <p className="page-lede">
              {t("analytics.scope")} <span className="chip chip-official">{scope}</span>{" "}
              {t("analytics.scopeSlice", { n: summary.configuration.scope_task_count })}
              {summary.configuration.scope_tasks_without_runs !== "none"
                ? t("analytics.scopeMissing", {
                    tasks: summary.configuration.scope_tasks_without_runs,
                  })
                : ""}
              . <Link to="/analytics">{t("analytics.viewAll")}</Link>
            </p>
          ) : null}
        </div>
      </header>

      <div className="analytics-grid">
        <section className="analytics-card" aria-label="Outcome versus process">
          <h3>{t("analytics.quadrant")}</h3>
          <table className="quadrant-table">
            <thead>
              <tr>
                <th scope="col">{t("analytics.quadrantCorner")}</th>
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
          <h3>{t("analytics.errorDistribution")}</h3>
          {summary.primary_error_distribution.length === 0 && (
            <p className="empty-lane">{t("analytics.noInvalid")}</p>
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
                  {entry.human_count > 0 &&
                    ` · ${t("analytics.humanCount", { n: entry.human_count })}`}
                  {entry.evaluator_count > 0 &&
                    ` · ${t("analytics.evaluatorCount", { n: entry.evaluator_count })}`}
                </span>
              </span>
            </div>
          ))}
        </section>
      </div>

      <section className="analytics-card" aria-label="Required metrics">
        <h3>{t("analytics.requiredMetrics")}</h3>
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">{t("analytics.col.metric")}</th>
              <th scope="col">{t("analytics.col.value")}</th>
              <th scope="col">n / d</th>
              <th scope="col">{t("analytics.col.provenance")}</th>
              <th scope="col">{t("analytics.col.exclusions")}</th>
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
                      <summary>
                        {t("analytics.excludedCount", { n: entry.exclusions.length })}
                      </summary>
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
        <h3>{t("analytics.byDifficulty")}</h3>
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">{t("analytics.col.difficulty")}</th>
              <th scope="col">{t("analytics.col.runs")}</th>
              <th scope="col">{t("analytics.col.resolved")}</th>
              <th scope="col">{t("analytics.col.outcomeRate")}</th>
              <th scope="col">{t("analytics.col.processValid")}</th>
              <th scope="col">{t("analytics.col.processRate")}</th>
              <th scope="col">{t("analytics.col.inconclusive")}</th>
              <th scope="col">{t("analytics.col.provenance")}</th>
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
          {t("analytics.declineObserved")} <strong>{summary.observed_decline_interval}</strong> ·{" "}
          {t("analytics.declineSupported")}{" "}
          <strong>{summary.statistically_supported_decline_interval}</strong>{" "}
          {t("analytics.declineConfig", {
            seed: summary.configuration.bootstrap_seed,
            n: summary.configuration.bootstrap_resamples,
          })}
        </p>
      </section>

      <section className="analytics-card" aria-label="Agent effort">
        <h3>{t("analytics.effort")}</h3>
        <p className="record-meta">{t("analytics.effortNote")}</p>
        {summary.efficiency.length === 0 && <p className="empty-lane">{t("analytics.noRuns")}</p>}
        {summary.efficiency.length > 0 && (
          <table className="run-table">
            <thead>
              <tr>
                <th scope="col">{t("analytics.col.difficulty")}</th>
                <th scope="col">{t("analytics.col.outcome")}</th>
                <th scope="col">{t("analytics.col.runs")}</th>
                <th scope="col">{t("analytics.col.medianSteps")}</th>
                <th scope="col">{t("analytics.col.stepsRange")}</th>
                <th scope="col">{t("analytics.col.medianToolCalls")}</th>
                <th scope="col">{t("analytics.col.provenance")}</th>
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
                      t("analytics.withoutTrajectory", {
                        n: row.run_count - row.runs_with_trajectory,
                      })}
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
          <h3>{t("analytics.excludedRuns")}</h3>
          {summary.excluded_runs.length === 0 && <p className="empty-lane">{t("common.none")}</p>}
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
          <h3>{t("analytics.cases")}</h3>
          {summary.cases.length === 0 && <p className="empty-lane">{t("analytics.noCases")}</p>}
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
                      ? t("analytics.rejectedFalsePositive")
                      : t("analytics.humanAdjudication", { adjudication: entry.adjudication })}
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
