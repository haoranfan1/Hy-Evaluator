import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { fetchRuns } from "../api";
import { useI18n } from "../i18n";

// Statuses render untranslated: they are evaluation data, not chrome.
function StatusChip({ value, fallback }: { value: string | null; fallback: string }) {
  if (!value) {
    return <span className="chip chip-pending">{fallback}</span>;
  }
  return <span className={`chip chip-${value}`}>{value}</span>;
}

export function RunsPage() {
  const { t } = useI18n();
  const runs = useQuery({ queryKey: ["runs"], queryFn: fetchRuns, retry: false });
  const [outcomeFilter, setOutcomeFilter] = useState("all");
  const [processFilter, setProcessFilter] = useState("all");

  const visible = (runs.data?.runs ?? []).filter(
    (run) =>
      (outcomeFilter === "all" || run.outcome_status === outcomeFilter) &&
      (processFilter === "all" || run.process_status === processFilter),
  );

  return (
    <section>
      <header className="page-head">
        <div>
          <h2>{t("runs.title")}</h2>
          <p className="page-lede">{t("runs.lede")}</p>
        </div>
        <div className="filters">
          <label>
            {t("runs.filter.outcome")}
            <select
              value={outcomeFilter}
              onChange={(event) => setOutcomeFilter(event.target.value)}
            >
              <option value="all">{t("runs.filter.all")}</option>
              <option value="resolved">resolved</option>
              <option value="unresolved">unresolved</option>
              <option value="inconclusive">inconclusive</option>
            </select>
          </label>
          <label>
            {t("runs.filter.process")}
            <select
              value={processFilter}
              onChange={(event) => setProcessFilter(event.target.value)}
            >
              <option value="all">{t("runs.filter.all")}</option>
              <option value="valid">valid</option>
              <option value="invalid">invalid</option>
              <option value="inconclusive">inconclusive</option>
            </select>
          </label>
        </div>
      </header>

      {runs.isPending && <p>{t("runs.loading")}</p>}
      {runs.isError && <p role="alert">{t("runs.error")}</p>}
      {runs.data && (
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">{t("runs.col.run")}</th>
              <th scope="col">{t("runs.col.repository")}</th>
              <th scope="col">{t("runs.col.difficulty")}</th>
              <th scope="col">{t("runs.col.outcome")}</th>
              <th scope="col">{t("runs.col.process")}</th>
              <th scope="col">{t("runs.col.firstError")}</th>
              <th scope="col">{t("runs.col.reviews")}</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((run) => (
              <tr key={run.run_id}>
                <td>
                  <Link className="run-link" to={`/runs/${encodeURIComponent(run.run_id)}`}>
                    {run.run_id}
                  </Link>
                </td>
                <td>{run.repository}</td>
                <td>{run.difficulty}</td>
                <td>
                  <StatusChip value={run.outcome_status} fallback={t("common.notEvaluated")} />
                </td>
                <td>
                  <StatusChip value={run.process_status} fallback={t("common.notEvaluated")} />
                </td>
                <td>
                  {run.first_error?.location === "located" && (
                    <span>
                      {t("common.step", { n: run.first_error.step_id ?? "?" })} ·{" "}
                      {run.first_error.primary_category}
                    </span>
                  )}
                  {run.first_error?.location === "unlocatable" && (
                    <span>unlocatable · {run.first_error.primary_category}</span>
                  )}
                  {(!run.first_error || run.first_error.location === "none") && <span>—</span>}
                </td>
                <td>{run.review_count}</td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-lane">
                  {t("runs.empty")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
