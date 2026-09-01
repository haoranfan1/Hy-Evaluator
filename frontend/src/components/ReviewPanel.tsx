import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { Finding, FindingDecision, HumanLabel, HumanReview } from "../api";
import { postAdjudication, postInitialReview } from "../api";
import { useI18n } from "../i18n";

const CATEGORIES = [
  "task_interpretation",
  "investigation",
  "reasoning",
  "action_execution",
  "implementation",
  "verification",
  "process_integrity",
];

type LabelState = {
  process_status: "valid" | "invalid" | "inconclusive";
  first_error_location: "none" | "located" | "unlocatable";
  step: string;
  category: string;
  notes: string;
};

const EMPTY_LABEL: LabelState = {
  process_status: "invalid",
  first_error_location: "located",
  step: "",
  category: CATEGORIES[0],
  notes: "",
};

function toHumanLabel(state: LabelState): HumanLabel {
  const located = state.process_status !== "valid" && state.first_error_location === "located";
  const needsCategory = state.process_status === "invalid" || located;
  return {
    process_status: state.process_status,
    first_error_location: state.process_status === "valid" ? "none" : state.first_error_location,
    first_error_step_id: located && state.step !== "" ? Number(state.step) : null,
    primary_category: needsCategory ? state.category : null,
    notes: state.notes,
  };
}

function LabelFields({
  legend,
  state,
  onChange,
}: {
  legend: string;
  state: LabelState;
  onChange: (state: LabelState) => void;
}) {
  const { t } = useI18n();
  const showLocation = state.process_status !== "valid";
  const showStep = showLocation && state.first_error_location === "located";
  const showCategory = showLocation && state.first_error_location !== "none";
  return (
    <fieldset className="label-fields">
      <legend>{legend}</legend>
      <label>
        {t("review.processStatus")}
        <select
          value={state.process_status}
          onChange={(event) =>
            onChange({ ...state, process_status: event.target.value as LabelState["process_status"] })
          }
        >
          <option value="valid">valid</option>
          <option value="invalid">invalid</option>
          <option value="inconclusive">inconclusive</option>
        </select>
      </label>
      {showLocation && (
        <label>
          {t("review.firstError")}
          <select
            value={state.first_error_location}
            onChange={(event) =>
              onChange({
                ...state,
                first_error_location: event.target.value as LabelState["first_error_location"],
              })
            }
          >
            <option value="located">located</option>
            <option value="unlocatable">unlocatable</option>
            <option value="none">none</option>
          </select>
        </label>
      )}
      {showStep && (
        <label>
          {t("review.stepId")}
          <input
            type="number"
            min={1}
            value={state.step}
            onChange={(event) => onChange({ ...state, step: event.target.value })}
          />
        </label>
      )}
      {showCategory && (
        <label>
          {t("review.primaryCategory")}
          <select
            value={state.category}
            onChange={(event) => onChange({ ...state, category: event.target.value })}
          >
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        {t("review.labelNotes")}
        <textarea
          rows={2}
          value={state.notes}
          onChange={(event) => onChange({ ...state, notes: event.target.value })}
        />
      </label>
    </fieldset>
  );
}

function describeLabel(t: ReturnType<typeof useI18n>["t"], label: HumanLabel): string {
  const parts: string[] = [label.process_status];
  if (label.first_error_location === "located") {
    parts.push(t("review.firstErrorAtStep", { n: label.first_error_step_id ?? "?" }));
  } else {
    parts.push(t("review.firstErrorLocation", { location: label.first_error_location }));
  }
  if (label.primary_category) {
    parts.push(label.primary_category);
  }
  return parts.join(" · ");
}

export function ReviewPanel({
  runId,
  evaluationId,
  reviews,
  findings,
}: {
  runId: string;
  evaluationId: string;
  reviews: HumanReview[];
  findings: Finding[];
}) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [reviewer, setReviewer] = useState("reviewer-1");
  const [label, setLabel] = useState(EMPTY_LABEL);
  const [adjudication, setAdjudication] = useState<
    "accept" | "edit" | "reject" | "needs_more_evidence"
  >("accept");
  const [decisions, setDecisions] = useState<Record<string, FindingDecision["decision"]>>({});

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["run", runId] });
  const initialMutation = useMutation({
    mutationFn: () =>
      postInitialReview(evaluationId, {
        reviewer_alias: reviewer,
        rubric_version: "process-rubric-v1",
        initial_label: toHumanLabel(label),
      }),
    onSuccess: refresh,
  });
  const adjudicationMutation = useMutation({
    mutationFn: () =>
      postAdjudication(evaluationId, {
        reviewer_alias: reviewer,
        rubric_version: "process-rubric-v1",
        adjudication,
        final_label: toHumanLabel(label),
        finding_decisions: Object.entries(decisions).map(([finding_id, decision]) => ({
          finding_id,
          decision,
          notes: "",
        })),
      }),
    onSuccess: refresh,
  });

  const adjudicated = reviews.some((review) => review.final_label !== null);
  const hasInitial = reviews.length > 0;

  if (adjudicated) {
    return (
      <section className="review-panel" aria-label="Review history">
        <h3>{t("review.history")}</h3>
        {reviews.map((review) => (
          <article className="review-version" key={review.review_id}>
            <p className="review-head">
              <span className="chip">v{review.review_version}</span>
              <span>{review.reviewer_alias}</span>
              {review.adjudication && (
                <span className={`chip chip-${review.adjudication}`}>{review.adjudication}</span>
              )}
            </p>
            <p className="review-label">
              {t("review.initialLabelIs", { label: describeLabel(t, review.initial_label) })}
            </p>
            {review.final_label && (
              <p className="review-label">
                {t("review.finalLabelIs", { label: describeLabel(t, review.final_label) })}
              </p>
            )}
            {review.finding_decisions.length > 0 && (
              <ul className="decision-list">
                {review.finding_decisions.map((decision) => (
                  <li key={decision.finding_id}>
                    <code>{decision.finding_id}</code> — {decision.decision}
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </section>
    );
  }

  if (!hasInitial) {
    return (
      <section className="review-panel" aria-label="Blinded initial review">
        <h3>{t("review.blindedInitial")}</h3>
        <p className="panel-note">{t("review.blindedNote")}</p>
        <label>
          {t("review.reviewerAlias")}
          <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
        </label>
        <LabelFields legend={t("review.yourLabel")} state={label} onChange={setLabel} />
        <button
          type="button"
          className="primary-action"
          disabled={initialMutation.isPending}
          onClick={() => initialMutation.mutate()}
        >
          {t("review.saveInitial")}
        </button>
        {initialMutation.isError && (
          <p role="alert" className="form-error">
            {(initialMutation.error as Error).message}
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="review-panel" aria-label="Adjudication">
      <h3>{t("review.adjudication")}</h3>
      <p className="review-label">
        {t("review.initialLabelIs", { label: describeLabel(t, reviews[0].initial_label) })}
      </p>
      <label>
        {t("review.decision")}
        <select
          value={adjudication}
          onChange={(event) => setAdjudication(event.target.value as typeof adjudication)}
        >
          <option value="accept">accept</option>
          <option value="edit">edit</option>
          <option value="reject">reject</option>
          <option value="needs_more_evidence">needs_more_evidence</option>
        </select>
      </label>
      {findings.length > 0 && (
        <fieldset className="label-fields">
          <legend>{t("review.findingDecisions")}</legend>
          {findings.map((finding) => (
            <label key={finding.finding_id}>
              <code>{finding.finding_id}</code>
              <select
                value={decisions[finding.finding_id] ?? "accept"}
                onChange={(event) =>
                  setDecisions({
                    ...decisions,
                    [finding.finding_id]: event.target
                      .value as FindingDecision["decision"],
                  })
                }
              >
                <option value="accept">accept</option>
                <option value="edit">edit</option>
                <option value="reject">reject</option>
                <option value="needs_more_evidence">needs_more_evidence</option>
              </select>
            </label>
          ))}
        </fieldset>
      )}
      <LabelFields legend={t("review.finalLabel")} state={label} onChange={setLabel} />
      <button
        type="button"
        className="primary-action"
        disabled={adjudicationMutation.isPending}
        onClick={() => adjudicationMutation.mutate()}
      >
        {t("review.appendAdjudication")}
      </button>
      {adjudicationMutation.isError && (
        <p role="alert" className="form-error">
          {(adjudicationMutation.error as Error).message}
        </p>
      )}
    </section>
  );
}
