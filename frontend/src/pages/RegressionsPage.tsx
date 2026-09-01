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
import type { MessageKey } from "../i18n";
import { useI18n } from "../i18n";

// Renders the committed validation evidence (regression cards and
// judge-stability records) exactly as recorded under results/. Every number on
// this page comes from a frozen file; nothing is recomputed at view time.

const SCORE_FAMILIES: { key: string; label: MessageKey; betterWhen: "lower" | "higher" }[] = [
  { key: "false_positives", label: "regressions.falsePositives", betterWhen: "lower" },
  { key: "detection", label: "regressions.detection", betterWhen: "higher" },
  { key: "exact_localization", label: "regressions.exactLocalization", betterWhen: "higher" },
  { key: "within_one_localization", label: "regressions.withinOne", betterWhen: "higher" },
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
  const { t } = useI18n();
  if (stored.n === reevaluated.n) {
    return <span className="score-unchanged">{t("regressions.unchanged")}</span>;
  }
  const improved = betterWhen === "lower" ? reevaluated.n < stored.n : reevaluated.n > stored.n;
  return (
    <span className={`chip ${improved ? "chip-pass" : "chip-fail"}`}>
      {improved ? t("regressions.improved") : t("regressions.regressed")}
    </span>
  );
}

function VerdictCell({ status, step }: { status: string; step: number | null }) {
  const { t } = useI18n();
  return (
    <>
      <span className={`chip chip-${status}`}>{status}</span>{" "}
      <span className="step-ref">{step === null ? "—" : t("common.step", { n: step })}</span>
    </>
  );
}

export function agreement(
  lane: { process_status: string; first_error_step: number | null },
  human: { process_status: string; first_error_step: number | null },
): { label: MessageKey; chip: string } {
  if (lane.process_status !== human.process_status) {
    // An honest abstention is not the same failure as a wrong verdict.
    if (lane.process_status === "inconclusive") {
      return { label: "regressions.abstained", chip: "chip-warning" };
    }
    return { label: "regressions.differsFromHuman", chip: "chip-fail" };
  }
  if (human.first_error_step !== null && lane.first_error_step !== human.first_error_step) {
    return { label: "regressions.stepDiffers", chip: "chip-warning" };
  }
  return { label: "regressions.matchesHuman", chip: "chip-pass" };
}

function RunRow({ run, storedLabel, reevaluatedLabel }: {
  run: RegressionRun;
  storedLabel: string;
  reevaluatedLabel: string;
}) {
  const { t } = useI18n();
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
        <span className={`chip ${storedAgreement.chip}`}>{t(storedAgreement.label)}</span>
      </td>
      <td>
        <VerdictCell
          status={run.reevaluated.process_status}
          step={run.reevaluated.first_error_step}
        />
        <br />
        <span className={`chip ${reevaluatedAgreement.chip}`}>{t(reevaluatedAgreement.label)}</span>
      </td>
      <td>
        <details>
          <summary>{t("regressions.evidenceSummary")}</summary>
          <ul className="regression-evidence">
            {check && (
              <li>
                <span className={`chip chip-${check.status}`}>
                  {t("regressions.protectedPaths", { status: check.status })}
                </span>{" "}
                {check.summary}
              </li>
            )}
            {run.reevaluated.exclusions.length > 0 && (
              <li>
                {t("regressions.exclusions", {
                  version: reevaluatedLabel,
                  reasons: run.reevaluated.exclusions.join(", "),
                })}
              </li>
            )}
            {run.reevaluated.semantic_condensation && (
              <li>
                <span className="chip chip-semantic">{t("regressions.condensedInput")}</span>{" "}
                {run.reevaluated.semantic_condensation}
              </li>
            )}
            <li className="step-ref">
              {t("regressions.evaluationStatus", {
                stored: storedLabel,
                storedStatus: run.stored.status,
                reevaluated: reevaluatedLabel,
                reevaluatedStatus: run.reevaluated.status,
              })}
            </li>
          </ul>
        </details>
      </td>
    </tr>
  );
}

function RegressionCardSection({ file, card }: { file: string; card: RegressionCard }) {
  const { t } = useI18n();
  const storedLabel = shortVersion(card.stored_version);
  const reevaluatedLabel = shortVersion(card.reevaluated_version);
  return (
    <section className="analytics-card" aria-label={`Regression card ${reevaluatedLabel}`}>
      <h3>
        {card.stored_version} → {card.reevaluated_version}
      </h3>
      <p className="record-meta">
        <span className="chip chip-official">{card.slice_id}</span>{" "}
        {t("regressions.recorded", { date: card.recorded_at.slice(0, 10) })} ·{" "}
        <code className="record-file">{file}</code>
      </p>
      <ClampedText className="card-note" text={card.note} />

      <table className="run-table score-table">
        <thead>
          <tr>
            <th scope="col">{t("regressions.scoreCol")}</th>
            <th scope="col">{storedLabel}</th>
            <th scope="col">{reevaluatedLabel}</th>
            <th scope="col">{t("regressions.changeCol")}</th>
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
                <td>{t(family.label)}</td>
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
            <th scope="col">{t("regressions.col.task")}</th>
            <th scope="col">{t("regressions.col.human")}</th>
            <th scope="col">{t("regressions.col.stored", { version: storedLabel })}</th>
            <th scope="col">{t("regressions.col.reevaluated", { version: reevaluatedLabel })}</th>
            <th scope="col">{t("regressions.col.evidence")}</th>
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
  const { t } = useI18n();
  const { summary } = record;
  return (
    <section className="analytics-card" aria-label={`Judge stability for ${record.subject}`}>
      <h3>
        <code>{record.subject}</code>
      </h3>
      <p className="record-meta">
        {t("stability.meta", { n: record.repeats, date: record.recorded_at.slice(0, 10) })}{" "}
        <span className={`chip ${summary.verdict_unanimous ? "chip-pass" : "chip-fail"}`}>
          {summary.verdict_unanimous ? t("stability.unanimous") : t("stability.split")}
        </span>{" "}
        {summary.verdicts.map((verdict) => (
          <span key={verdict} className={`chip chip-${verdict}`}>
            {verdict}
          </span>
        ))}{" "}
        {summary.first_error_steps.length > 0 && (
          <span className={`chip ${summary.step_unanimous ? "chip-pass" : "chip-warning"}`}>
            {t("stability.firstErrorStep", { steps: summary.first_error_steps.join(", ") })}
          </span>
        )}
      </p>
      <p className="record-meta">
        {t("stability.judgeLine", {
          model: record.judge.model,
          effort: record.judge.reasoning_effort,
          temperature: record.judge.temperature,
          topP: record.judge.top_p,
        })}{" "}
        {record.judge.rubric_version} · {record.judge.semantic_prompt_version} ·{" "}
        <code className="record-file">{file}</code>
      </p>
      <table className="run-table">
        <thead>
          <tr>
            <th scope="col">{t("stability.col.attempt")}</th>
            <th scope="col">{t("stability.col.status")}</th>
            <th scope="col">{t("stability.col.verdict")}</th>
            <th scope="col">{t("stability.col.firstError")}</th>
            <th scope="col">{t("stability.col.category")}</th>
            <th scope="col">{t("stability.col.findings")}</th>
            <th scope="col">{t("stability.col.repairs")}</th>
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
                  ? t("common.step", { n: attempt.first_error_step ?? "?" })
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
  const { t } = useI18n();
  const records = useQuery({
    queryKey: ["validation-records"],
    queryFn: fetchValidationRecords,
    retry: false,
  });

  if (records.isPending) {
    return <p>{t("regressions.loading")}</p>;
  }
  if (records.isError || !records.data) {
    return <p role="alert">{t("regressions.error")}</p>;
  }
  const { regression_cards, judge_stability, unreadable } = records.data;
  // The API sorts oldest-first; the newest card is the headline result.
  const cards = [...regression_cards].reverse();
  const stability = [...judge_stability].reverse();

  return (
    <section>
      <header className="page-head">
        <div>
          <h2>{t("regressions.title")}</h2>
          <p className="page-lede">{t("regressions.lede")}</p>
        </div>
      </header>

      {unreadable.length > 0 && (
        <section className="analytics-card" role="alert" aria-label="Unreadable records">
          <h3>{t("regressions.unreadable")}</h3>
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
        <p className="empty-lane">{t("regressions.empty")}</p>
      )}

      {cards.map((entry) => (
        <RegressionCardSection key={entry.file} file={entry.file} card={entry.card} />
      ))}

      {stability.length > 0 && (
        <header className="page-head">
          <div>
            <h2>{t("stability.title")}</h2>
            <p className="page-lede">{t("stability.lede")}</p>
          </div>
        </header>
      )}
      {stability.map((entry) => (
        <StabilitySection key={entry.file} file={entry.file} record={entry.record} />
      ))}
    </section>
  );
}
