import { ClampedText } from "./OutputBlock";
import type { DeterministicCheck, EvidenceReference, Finding } from "../api";
import { citedStepIds } from "../api";

export type TabName = "timeline" | "patch" | "verifier" | "task";

export type Selection =
  | { kind: "check"; id: string }
  | { kind: "finding"; id: string }
  | null;

type Props = {
  checks: DeterministicCheck[];
  findings: Finding[];
  findingsHiddenNote?: string;
  selection: Selection;
  selectedStep: number | null;
  onSelect: (selection: Selection) => void;
  onOpenTab: (tab: TabName) => void;
  onSelectStep: (stepId: number) => void;
};

function citesStep(evidence: EvidenceReference[], stepId: number | null): boolean {
  return stepId !== null && citedStepIds(evidence).has(stepId);
}

function EvidenceChips({
  evidence,
  onOpenTab,
  onSelectStep,
}: {
  evidence: EvidenceReference[];
  onOpenTab: (tab: TabName) => void;
  onSelectStep: (stepId: number) => void;
}) {
  return (
    <p className="evidence-chips">
      {evidence.map((reference, index) => {
        if (reference.kind === "atif_step") {
          return (
            <button
              key={index}
              type="button"
              className="evidence-chip"
              onClick={() => {
                onSelectStep(reference.step_id);
                onOpenTab("timeline");
              }}
            >
              step {reference.step_id}
              {reference.tool_call_id ? ` · ${reference.tool_call_id}` : ""}
            </button>
          );
        }
        if (reference.kind === "patch") {
          return (
            <button
              key={index}
              type="button"
              className="evidence-chip"
              onClick={() => onOpenTab("patch")}
            >
              patch · {reference.file}
              {reference.line ? `:${reference.line}` : ""}
            </button>
          );
        }
        if (reference.kind === "verifier") {
          return (
            <button
              key={index}
              type="button"
              className="evidence-chip"
              onClick={() => onOpenTab("verifier")}
            >
              verifier{reference.test_name ? ` · ${reference.test_name}` : ""}
            </button>
          );
        }
        return (
          <button
            key={index}
            type="button"
            className="evidence-chip"
            onClick={() => onOpenTab("task")}
          >
            task · {reference.field}
          </button>
        );
      })}
    </p>
  );
}

export function EvidencePanel({
  checks,
  findings,
  findingsHiddenNote,
  selection,
  selectedStep,
  onSelect,
  onOpenTab,
  onSelectStep,
}: Props) {
  return (
    <aside className="evidence-panel">
      {selectedStep !== null && (
        <p className="panel-note">
          Showing evidence lanes. Items citing step {selectedStep} are marked.
        </p>
      )}

      <section aria-labelledby="findings-lane">
        <h3 id="findings-lane">Findings</h3>
        {findingsHiddenNote !== undefined && (
          <p className="empty-lane">{findingsHiddenNote}</p>
        )}
        {findingsHiddenNote === undefined && findings.length === 0 && (
          <p className="empty-lane">No findings.</p>
        )}
        {findings.map((finding) => {
          const active = selection?.kind === "finding" && selection.id === finding.finding_id;
          const classes = [
            "evidence-item",
            `severity-${finding.severity}`,
            active ? "evidence-selected" : "",
            citesStep(finding.evidence, selectedStep) ? "evidence-cites-step" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <article className={classes} key={finding.finding_id} data-testid={finding.finding_id}>
              <button
                type="button"
                className="evidence-head"
                aria-pressed={active}
                onClick={() =>
                  onSelect(active ? null : { kind: "finding", id: finding.finding_id })
                }
              >
                <span className={`chip chip-${finding.severity}`}>{finding.severity}</span>
                <span className={`chip chip-${finding.source}`}>{finding.source}</span>
                <span className="chip chip-category">{finding.category}</span>
                {citesStep(finding.evidence, selectedStep) && (
                  <span className="chip chip-cites">cites step {selectedStep}</span>
                )}
              </button>
              <ClampedText className="evidence-summary" text={finding.summary} />
              {active && (
                <>
                  <p className="evidence-detail">{finding.explanation}</p>
                  <p className="evidence-feedback">{finding.feedback}</p>
                  {finding.downstream_step_ids.length > 0 && (
                    <p className="evidence-chips propagation-row">
                      <span className="propagation-label">recorded propagation:</span>
                      {finding.downstream_step_ids.map((stepId) => (
                        <button
                          key={stepId}
                          type="button"
                          className="evidence-chip"
                          onClick={() => {
                            onSelectStep(stepId);
                            onOpenTab("timeline");
                          }}
                        >
                          step {stepId}
                        </button>
                      ))}
                    </p>
                  )}
                </>
              )}
              <EvidenceChips
                evidence={finding.evidence}
                onOpenTab={onOpenTab}
                onSelectStep={onSelectStep}
              />
            </article>
          );
        })}
      </section>

      <section aria-labelledby="checks-lane">
        <h3 id="checks-lane">Deterministic checks</h3>
        {checks.map((check) => {
          const active = selection?.kind === "check" && selection.id === check.check_id;
          const classes = [
            "evidence-item",
            `status-${check.status}`,
            active ? "evidence-selected" : "",
            citesStep(check.evidence, selectedStep) ? "evidence-cites-step" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <article className={classes} key={check.check_id} data-testid={check.check_id}>
              <button
                type="button"
                className="evidence-head"
                aria-pressed={active}
                onClick={() => onSelect(active ? null : { kind: "check", id: check.check_id })}
              >
                <span className={`chip chip-${check.status}`}>{check.status}</span>
                {check.hard_process_failure && (
                  <span className="chip chip-critical">hard failure</span>
                )}
                {citesStep(check.evidence, selectedStep) && (
                  <span className="chip chip-cites">cites step {selectedStep}</span>
                )}
                <span className="check-id">{check.check_id}</span>
              </button>
              <ClampedText className="evidence-summary" text={check.summary} />
              {check.evidence.length > 0 && (
                <EvidenceChips
                  evidence={check.evidence}
                  onOpenTab={onOpenTab}
                  onSelectStep={onSelectStep}
                />
              )}
            </article>
          );
        })}
      </section>
    </aside>
  );
}
