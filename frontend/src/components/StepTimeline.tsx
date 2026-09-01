import type { FirstError, TrajectoryStep } from "../api";
import { textOf } from "../api";
import { ClampedText, CommandBlock, ObservationBlock } from "./OutputBlock";

const NO_STEPS: ReadonlySet<number> = new Set();

type Props = {
  steps: TrajectoryStep[];
  firstError: FirstError | null;
  highlightedSteps: Set<number>;
  // Steps the selected finding records as downstream of its error — recorded
  // evidence from the evaluation, never inferred in the UI.
  downstreamSteps?: ReadonlySet<number>;
  propagationOrigin?: number | null;
  selectedStep: number | null;
  onSelectStep: (stepId: number | null) => void;
};

export function StepTimeline({
  steps,
  firstError,
  highlightedSteps,
  downstreamSteps = NO_STEPS,
  propagationOrigin = null,
  selectedStep,
  onSelectStep,
}: Props) {
  return (
    <ol className="timeline" aria-label="Trajectory steps">
      {steps.map((step) => {
        const isFirstError = firstError?.location === "located" && firstError.step_id === step.step_id;
        const isDownstream = downstreamSteps.has(step.step_id);
        const classes = [
          "step",
          `step-${step.source}`,
          highlightedSteps.has(step.step_id) ? "step-cited" : "",
          isDownstream ? "step-downstream" : "",
          selectedStep === step.step_id ? "step-selected" : "",
          isFirstError ? "step-first-error" : "",
        ]
          .filter(Boolean)
          .join(" ");
        // Harbor's chat-completions conversion leaves source_call_id null on
        // real runs, so results that match no tool call attach to the step
        // itself — dropping them would hide every real observation.
        const results = step.observation?.results ?? [];
        const callIds = new Set((step.tool_calls ?? []).map((call) => call.tool_call_id));
        const unmatched = results.filter(
          (result) => result.source_call_id == null || !callIds.has(result.source_call_id),
        );
        return (
          <li key={step.step_id} className={classes}>
            <button
              type="button"
              className="step-select"
              aria-pressed={selectedStep === step.step_id}
              onClick={() => onSelectStep(selectedStep === step.step_id ? null : step.step_id)}
            >
              <span className="step-id">Step {step.step_id}</span>
              <span className={`chip chip-${step.source}`}>{step.source}</span>
              {isFirstError && <span className="chip chip-first-error">First error</span>}
              {isDownstream && (
                <span className="chip chip-downstream">
                  {propagationOrigin === null
                    ? "downstream"
                    : `downstream of step ${propagationOrigin}`}
                </span>
              )}
            </button>
            <ClampedText className="step-message" text={textOf(step.message)} threshold={600} />
            {(step.tool_calls ?? []).map((call) => (
              <div className="tool-call" key={call.tool_call_id}>
                <p className="tool-call-head">
                  <code>{call.function_name}</code>
                  <span className="tool-call-id">{call.tool_call_id}</span>
                  {firstError?.location === "located" &&
                    firstError.step_id === step.step_id &&
                    firstError.tool_call_id === call.tool_call_id && (
                      <span className="chip chip-first-error">first-error call</span>
                    )}
                </p>
                <CommandBlock args={call.arguments} />
                {results
                  .filter((result) => result.source_call_id === call.tool_call_id)
                  .map((result, index) => (
                    <ObservationBlock content={result.content} key={index} />
                  ))}
              </div>
            ))}
            {unmatched.map((result, index) => (
              <ObservationBlock content={result.content} key={`step-${index}`} />
            ))}
          </li>
        );
      })}
    </ol>
  );
}
