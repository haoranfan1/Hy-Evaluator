import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";

import { citedStepIds, fetchRunDetail, fetchTrajectory } from "../api";
import { PatchView, TaskView, VerifierView } from "../components/ArtifactViews";
import type { Selection, TabName } from "../components/EvidencePanel";
import { EvidencePanel } from "../components/EvidencePanel";
import { ReviewPanel } from "../components/ReviewPanel";
import { ClampedText } from "../components/OutputBlock";
import { StepTimeline } from "../components/StepTimeline";
import type { MessageKey } from "../i18n";
import { useI18n } from "../i18n";

const TABS: { id: TabName; label: MessageKey }[] = [
  { id: "timeline", label: "run.tab.timeline" },
  { id: "patch", label: "run.tab.patch" },
  { id: "verifier", label: "run.tab.verifier" },
  { id: "task", label: "run.tab.task" },
];

export function RunDetailPage() {
  const { t } = useI18n();
  const { runId = "" } = useParams();
  const detail = useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRunDetail(runId),
    retry: false,
  });
  const trajectory = useQuery({
    queryKey: ["trajectory", runId],
    queryFn: () => fetchTrajectory(runId),
    retry: false,
  });

  const [tab, setTab] = useState<TabName>("timeline");
  const [selection, setSelection] = useState<Selection>(null);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);

  const evaluation = detail.data?.evaluation ?? null;

  const highlightedSteps = useMemo(() => {
    if (!evaluation || !selection) {
      return new Set<number>();
    }
    const items =
      selection.kind === "finding"
        ? evaluation.findings.filter((finding) => finding.finding_id === selection.id)
        : evaluation.deterministic_checks.filter((check) => check.check_id === selection.id);
    const ids = new Set<number>();
    for (const item of items) {
      for (const stepId of citedStepIds(item.evidence)) {
        ids.add(stepId);
      }
    }
    return ids;
  }, [evaluation, selection]);

  // Propagation overlay: the selected finding's recorded downstream steps.
  const selectedFinding =
    selection?.kind === "finding"
      ? (evaluation?.findings.find((finding) => finding.finding_id === selection.id) ?? null)
      : null;
  const downstreamSteps = useMemo(
    () => new Set(selectedFinding?.downstream_step_ids ?? []),
    [selectedFinding],
  );

  if (detail.isPending) {
    return <p>{t("run.loading")}</p>;
  }
  if (detail.isError || !detail.data) {
    return <p role="alert">{t("run.error")}</p>;
  }

  const { run, task, artifacts, reviews } = detail.data;
  const blinded = evaluation !== null && reviews.length === 0;
  const firstError = blinded ? null : (evaluation?.first_error ?? null);
  const firstErrorFindings = (evaluation?.findings ?? []).filter(
    (finding) =>
      firstError?.location === "located" &&
      finding.step_id === firstError.step_id &&
      (finding.severity === "error" || finding.severity === "critical"),
  );

  return (
    <section>
      <p className="breadcrumb">
        <Link to="/runs">{t("run.back")}</Link>
      </p>
      <header className="page-head">
        <div>
          <h2>{run.run_id}</h2>
          <p className="page-lede">
            {task.repository} · {t("run.difficulty")} {task.difficulty.label} · {run.agent.name}{" "}
            {run.agent.version}
          </p>
        </div>
        <div className="badges">
          <span className={`chip chip-${evaluation?.outcome_status ?? "pending"}`}>
            {t("run.outcome", {
              status: evaluation?.outcome_status ?? t("common.notEvaluated"),
            })}
          </span>
          {blinded ? (
            <span className="chip chip-pending">{t("run.processHidden")}</span>
          ) : (
            <span className={`chip chip-${evaluation?.process_status ?? "pending"}`}>
              {t("run.process", {
                status: evaluation?.process_status ?? t("common.notEvaluated"),
              })}
            </span>
          )}
          {!blinded && evaluation?.correct_result_invalid_process === true && (
            <span className="chip chip-critical">{t("run.correctResultInvalidProcess")}</span>
          )}
        </div>
      </header>

      {firstError?.location === "located" && (
        <div className="first-error-banner" role="note" aria-label="First error">
          <h3>
            {t("run.firstErrorAt", { n: firstError.step_id ?? "?" })}
            {firstError.tool_call_id && (
              <>
                {" "}
                · <code>{firstError.tool_call_id}</code>
              </>
            )}{" "}
            · {firstError.primary_category}
          </h3>
          {firstErrorFindings.map((finding) => (
            <ClampedText key={finding.finding_id} className="banner-summary" text={finding.summary} />
          ))}
        </div>
      )}
      {firstError?.location === "unlocatable" && (
        <div className="first-error-banner" role="note" aria-label="First error">
          <h3>{t("run.firstErrorUnlocatable")}</h3>
          <p>{t("run.primaryCategory", { category: firstError.primary_category ?? "—" })}</p>
        </div>
      )}
      {evaluation && !blinded && evaluation.process_status === "inconclusive" && (
        <div className="inconclusive-banner" role="note">
          <h3>{t("run.noVerdict")}</h3>
          <p>{t("run.noVerdictBody")}</p>
        </div>
      )}

      <div className="detail-layout">
        <div className="detail-main">
          <nav className="tabs" aria-label="Evidence tabs">
            {TABS.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className={tab === entry.id ? "tab tab-active" : "tab"}
                aria-pressed={tab === entry.id}
                onClick={() => setTab(entry.id)}
              >
                {t(entry.label)}
              </button>
            ))}
          </nav>

          {tab === "timeline" &&
            (trajectory.data ? (
              <StepTimeline
                steps={trajectory.data.steps}
                firstError={firstError}
                highlightedSteps={highlightedSteps}
                downstreamSteps={downstreamSteps}
                propagationOrigin={selectedFinding?.step_id ?? null}
                selectedStep={selectedStep}
                onSelectStep={setSelectedStep}
              />
            ) : trajectory.isError ? (
              <p role="alert">{t("run.trajectoryInvalid")}</p>
            ) : (
              <p>{t("run.trajectoryLoading")}</p>
            ))}
          {tab === "patch" && <PatchView patch={artifacts.patch} />}
          {tab === "verifier" && (
            <VerifierView
              checks={evaluation?.deterministic_checks ?? []}
              exclusions={evaluation?.exclusions ?? []}
              testOutput={artifacts.test_output}
              runLog={artifacts.run_log}
            />
          )}
          {tab === "task" && <TaskView task={task} />}
        </div>

        <div className="detail-side">
          {evaluation && (
            <ReviewPanel
              runId={run.run_id}
              evaluationId={evaluation.evaluation_id}
              reviews={reviews}
              findings={evaluation.findings}
            />
          )}
          <EvidencePanel
            checks={evaluation?.deterministic_checks ?? []}
            findings={blinded ? [] : (evaluation?.findings ?? [])}
            findingsHiddenNote={blinded ? t("evidence.hiddenWhileBlinded") : undefined}
            selection={selection}
            selectedStep={selectedStep}
            onSelect={setSelection}
            onOpenTab={setTab}
            onSelectStep={setSelectedStep}
          />
        </div>
      </div>
    </section>
  );
}
