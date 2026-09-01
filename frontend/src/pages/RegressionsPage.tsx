import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import {
  fetchValidationRecords,
  type JudgeStabilityRecord,
  type RegressionCard,
  type RegressionRun,
  type ScoreCount,
} from "../api";
import { ClampedText } from "../components/OutputBlock";

// Renders the committed validation evidence (regression cards and
// judge-stability records) exactly as recorded under results/. Every number on
// this page comes from a frozen file; nothing is recomputed at view time.

const SCORE_FAMILIES: { key: string; label: string; betterWhen: "lower" | "higher" }[] = [
  { key: "false_positives", label: "False positives (lower is better)", betterWhen: "lower" },
  { key: "detection", label: "Invalid-process detection", betterWhen: "higher" },
  { key: "exact_localization", label: "Exact first-error localization", betterWhen: "higher" },
  { key: "within_one_localization", label: "Localization within one step", betterWhen: "higher" },
];

function shortVersion(version: string): string {
  const match = /-v(\d+)$/.exec(version);
  return match ? `v${match[1]}` : version;
}

function ScoreDelta({
  betterWhen,
  stored,
  reevaluated,
}: {
  betterWhen: "lower" | "higher";
  stored: ScoreCount;
  reevaluated: ScoreCount;
}) {
  if (stored.n === reevaluated.n) {
    return <span className="score-unchanged">unchanged</span>;
  }
  const improved = betterWhen === "lower" ? reevaluated.n < stored.n : reevaluated.n > stored.n;
  return (
    <span className={`chip ${improved ? "chip-pass" : "chip-fail"}`}>
      {improved ? "improved" : "regressed"}
    </span>
  );
}

function VerdictCell({ status, step }: { status: string; step: number | null }) {
  return (
    <>
      <span className={`chip chip-${status}`}>{status}</span>{" "}
      <span className="step-ref">{step === null ? "—" : `step ${step}`}</span>
    </>
  );
}

export function agreement(
  lane: { process_status: string; first_error_step: number | null },
  human: { process_status: string; first_error_step: number | null },
): { label: string; chip: string } {
  if (lane.process_status !== human.process_status) {
    // An honest abstention is not the same failure as a wrong verdict.
    if (lane.process_status === "inconclusive") {
      return { label: "abstained", chip: "chip-warning" };
    }
    return { label: "differs from human", chip: "chip-fail" };
  }
  if (human.first_error_step !== null && lane.first_error_step !== human.first_error_step) {
    return { label: "step differs", chip: "chip-warning" };
  }
  return { label: "matches human", chip: "chip-pass" };
}

function RunRow({ run, storedLabel, reevaluatedLabel }: {
  run: RegressionRun;
  storedLabel: string;
  reevaluatedLabel: string;
}) {
  const storedAgreement = agreement(run.stored, run.human);
  const reevaluatedAgreement = agreement(run.reevaluated, run.human);
  const check = run.reevaluated.protected_check;
  return (
    <tr>
      <td>
        <Link to={`/runs/${run.run_id}`}>{run.task_id}</Link>
      </td>
      <td>
        <VerdictCell status={run.human.process_status} step={run.human.first_error_step} />
      </td>
      <td>
        <VerdictCell status={run.stored.process_status} step={run.stored.first_error_step} />
        <br />
        <span className={`chip ${storedAgreement.chip}`}>{storedAgreement.label}</span>
      </td>
      <td>
        <VerdictCell
          status={run.reevaluated.process_status}
          step={run.reevaluated.first_error_step}
        />
        <br />
        <span className={`chip ${reevaluatedAgreement.chip}`}>{reevaluatedAgreement.label}</span>
      </td>
      <td>
        <details>
          <summary>evidence</summary>
          <ul className="regression-evidence">
            {check && (
              <li>
                <span className={`chip chip-${check.status}`}>protected paths {check.status}</span>{" "}
                {check.summary}
              </li>
            )}
            {run.reevaluated.exclusions.length > 0 && (
              <li>
                {reevaluatedLabel} exclusions: {run.reevaluated.exclusions.join(", ")}
              </li>
            )}
            {run.reevaluated.semantic_condensation && (
              <li>
                <span className="chip chip-semantic">condensed input</span>{" "}
                {run.reevaluated.semantic_condensation}
              </li>
            )}
            <li className="step-ref">
              evaluation status: {storedLabel} {run.stored.status} · {reevaluatedLabel}{" "}
              {run.reevaluated.status}
            </li>
          </ul>
        </details>
      </td>
    </tr>
  );
}

function RegressionCardSection({ file, card }: { file: string; card: RegressionCard }) {
  const storedLabel = shortVersion(card.stored_version);
  const reevaluatedLabel = shortVersion(card.reevaluated_version);
  return (
    <section className="analytics-card" aria-label={`Regression card ${reevaluatedLabel}`}>
      <h3>
        {card.stored_version} → {card.reevaluated_version}
      </h3>
      <p className="record-meta">
        <span className="chip chip-official">{card.slice_id}</span> recorded{" "}
        {card.recorded_at.slice(0, 10)} · <code className="record-file">{file}</code>
      </p>
      <ClampedText className="card-note" text={card.note} />

      <table className="run-table score-table">
        <thead>
          <tr>
            <th scope="col">Check vs. frozen human labels</th>
            <th scope="col">{storedLabel}</th>
            <th scope="col">{reevaluatedLabel}</th>
            <th scope="col">Change</th>
          </tr>
        </thead>
        <tbody>
          {SCORE_FAMILIES.map((family) => {
            const stored = card.scores.stored?.[family.key];
            const reevaluated = card.scores.reevaluated?.[family.key];
            if (!stored || !reevaluated) {
              return null;
            }
            return (
              <tr key={family.key}>
                <td>{family.label}</td>
                <td>
                  {stored.n} / {stored.d}
                </td>
                <td>
                  {reevaluated.n} / {reevaluated.d}
                </td>
                <td>
                  <ScoreDelta
                    betterWhen={family.betterWhen}
                    stored={stored}
                    reevaluated={reevaluated}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <table className="run-table">
        <thead>
          <tr>
            <th scope="col">Task</th>
            <th scope="col">Human label</th>
            <th scope="col">{storedLabel} (stored)</th>
            <th scope="col">{reevaluatedLabel} (re-evaluated)</th>
            <th scope="col">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {card.runs.map((run) => (
            <RunRow
              key={run.run_id}
              run={run}
              storedLabel={storedLabel}
              reevaluatedLabel={reevaluatedLabel}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

function StabilitySection({ file, record }: { file: string; record: JudgeStabilityRecord }) {
  const { summary } = record;
  return (
    <section className="analytics-card" aria-label={`Judge stability for ${record.subject}`}>
      <h3>
        <code>{record.subject}</code>
      </h3>
      <p className="record-meta">
        {record.repeats} live repeats · recorded {record.recorded_at.slice(0, 10)} ·{" "}
        <span className={`chip ${summary.verdict_unanimous ? "chip-pass" : "chip-fail"}`}>
          {summary.verdict_unanimous ? "verdict unanimous" : "verdicts split"}
        </span>{" "}
        {summary.verdicts.map((verdict) => (
          <span key={verdict} className={`chip chip-${verdict}`}>
            {verdict}
          </span>
        ))}{" "}
        {summary.first_error_steps.length > 0 && (
          <span className={`chip ${summary.step_unanimous ? "chip-pass" : "chip-warning"}`}>
            first error step {summary.first_error_steps.join(", ")}
          </span>
        )}
      </p>
      <p className="record-meta">
        judge: {record.judge.model} · effort {record.judge.reasoning_effort} · temperature{" "}
        {record.judge.temperature} · top_p {record.judge.top_p} · {record.judge.rubric_version} ·{" "}
        {record.judge.semantic_prompt_version} · <code className="record-file">{file}</code>
      </p>
      <table className="run-table">
        <thead>
          <tr>
            <th scope="col">Attempt</th>
            <th scope="col">Status</th>
            <th scope="col">Verdict</th>
            <th scope="col">First error</th>
            <th scope="col">Category</th>
            <th scope="col">Findings</th>
            <th scope="col">Schema repairs</th>
          </tr>
        </thead>
        <tbody>
          {record.attempts.map((attempt) => (
            <tr key={attempt.attempt}>
              <td>{attempt.attempt}</td>
              <td>
                <span className={`chip chip-${attempt.status}`}>{attempt.status}</span>
              </td>
              <td>
                {attempt.process_status ? (
                  <span className={`chip chip-${attempt.process_status}`}>
                    {attempt.process_status}
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td>
                {attempt.first_error_location === "located"
                  ? `step ${attempt.first_error_step}`
                  : (attempt.first_error_location ?? "—")}
              </td>
              <td>{attempt.primary_category ?? "—"}</td>
              <td>{attempt.finding_count ?? "—"}</td>
              <td>{attempt.repair_retries ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function RegressionsPage() {
  const records = useQuery({
    queryKey: ["validation-records"],
    queryFn: fetchValidationRecords,
    retry: false,
  });

  if (records.isPending) {
    return <p>Loading committed validation records…</p>;
  }
  if (records.isError || !records.data) {
    return <p role="alert">Validation records could not be loaded from the local API.</p>;
  }
  const { regression_cards, judge_stability, unreadable } = records.data;
  // The API sorts oldest-first; the newest card is the headline result.
  const cards = [...regression_cards].reverse();
  const stability = [...judge_stability].reverse();

  return (
    <section>
      <header className="page-head">
        <div>
          <h2>Regression evidence</h2>
          <p className="page-lede">
            Frozen validation records committed under <code>results/</code>. Each regression card
            re-evaluates the frozen slice under a newer evaluator and scores both versions against
            the frozen adjudicated human labels; judge-stability records repeat the semantic judge
            on one input. This page renders the committed files read-only — nothing is recomputed.
          </p>
        </div>
      </header>

      {unreadable.length > 0 && (
        <section className="analytics-card" role="alert" aria-label="Unreadable records">
          <h3>Unreadable committed files</h3>
          <ul className="exclusion-list">
            {unreadable.map((entry) => (
              <li key={entry.file}>
                <code className="record-file">{entry.file}</code> — {entry.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      {cards.length === 0 && judge_stability.length === 0 && (
        <p className="empty-lane">
          No committed validation records found under <code>results/</code>.
        </p>
      )}

      {cards.map((entry) => (
        <RegressionCardSection key={entry.file} file={entry.file} card={entry.card} />
      ))}

      {stability.length > 0 && (
        <header className="page-head">
          <div>
            <h2>Judge stability</h2>
            <p className="page-lede">
              Repeated live judge calls on the same input, recorded at the judge&apos;s real
              sampling settings — the run-to-run variance the semantic lane has to live with.
            </p>
          </div>
        </header>
      )}
      {stability.map((entry) => (
        <StabilitySection key={entry.file} file={entry.file} record={entry.record} />
      ))}
    </section>
  );
}
