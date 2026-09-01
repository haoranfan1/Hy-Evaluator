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

const TABS: { id: TabName; label: string }[] = [
  { id: "timeline", label: "Timeline" },
  { id: "patch", label: "Patch" },
  { id: "verifier", label: "Verifier" },
  { id: "task", label: "Task" },
];

export function RunDetailPage() {
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
    return <p>Loading run…</p>;
  }
  if (detail.isError || !detail.data) {
    return <p role="alert">This run could not be loaded from the local API.</p>;
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
        <Link to="/runs">← All runs</Link>
      </p>
      <header className="page-head">
        <div>
          <h2>{run.run_id}</h2>
          <p className="page-lede">
            {task.repository} · difficulty {task.difficulty.label} · {run.agent.name}{" "}
            {run.agent.version}
          </p>
        </div>
        <div className="badges">
          <span className={`chip chip-${evaluation?.outcome_status ?? "pending"}`}>
            outcome: {evaluation?.outcome_status ?? "not evaluated"}
          </span>
          {blinded ? (
            <span className="chip chip-pending">process: hidden until your initial label</span>
          ) : (
            <span className={`chip chip-${evaluation?.process_status ?? "pending"}`}>
              process: {evaluation?.process_status ?? "not evaluated"}
            </span>
          )}
          {!blinded && evaluation?.correct_result_invalid_process === true && (
            <span className="chip chip-critical">correct result, invalid process</span>
          )}
        </div>
      </header>

      {firstError?.location === "located" && (
        <div className="first-error-banner" role="note" aria-label="First error">
          <h3>
            First error at step {firstError.step_id}
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
          <h3>A material error exists, but its first step is unlocatable</h3>
          <p>Primary category: {firstError.primary_category}</p>
        </div>
      )}
      {evaluation && !blinded && evaluation.process_status === "inconclusive" && (
        <div className="inconclusive-banner" role="note">
          <h3>No process verdict</h3>
          <p>
            The evidence cannot support a defensible judgment. Recorded reasons are listed in the
            verifier tab.
          </p>
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
                {entry.label}
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
              <p role="alert">The stored trajectory failed validation and cannot be shown.</p>
            ) : (
              <p>Loading trajectory…</p>
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
            findingsHiddenNote={
              blinded
                ? "Semantic findings are hidden until your blinded initial label is saved."
                : undefined
            }
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
