import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { fetchRuns } from "../api";

function StatusChip({ value }: { value: string | null }) {
  if (!value) {
    return <span className="chip chip-pending">not evaluated</span>;
  }
  return <span className={`chip chip-${value}`}>{value}</span>;
}

export function RunsPage() {
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
          <h2>Imported runs</h2>
          <p className="page-lede">
            Every run below has immutable artifacts; open one to inspect its evidence.
          </p>
        </div>
        <div className="filters">
          <label>
            Outcome
            <select
              value={outcomeFilter}
              onChange={(event) => setOutcomeFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="resolved">resolved</option>
              <option value="unresolved">unresolved</option>
              <option value="inconclusive">inconclusive</option>
            </select>
          </label>
          <label>
            Process
            <select
              value={processFilter}
              onChange={(event) => setProcessFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="valid">valid</option>
              <option value="invalid">invalid</option>
              <option value="inconclusive">inconclusive</option>
            </select>
          </label>
        </div>
      </header>

      {runs.isPending && <p>Loading runs…</p>}
      {runs.isError && <p role="alert">The run list could not be loaded from the local API.</p>}
      {runs.data && (
        <table className="run-table">
          <thead>
            <tr>
              <th scope="col">Run</th>
              <th scope="col">Repository</th>
              <th scope="col">Difficulty</th>
              <th scope="col">Outcome</th>
              <th scope="col">Process</th>
              <th scope="col">First error</th>
              <th scope="col">Reviews</th>
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
                  <StatusChip value={run.outcome_status} />
                </td>
                <td>
                  <StatusChip value={run.process_status} />
                </td>
                <td>
                  {run.first_error?.location === "located" && (
                    <span>
                      step {run.first_error.step_id} · {run.first_error.primary_category}
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
                  No runs match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
