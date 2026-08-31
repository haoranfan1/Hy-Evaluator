import type { FirstError, TrajectoryStep } from "../api";
import { textOf } from "../api";

type Props = {
  steps: TrajectoryStep[];
  firstError: FirstError | null;
  highlightedSteps: Set<number>;
  selectedStep: number | null;
  onSelectStep: (stepId: number | null) => void;
};

export function StepTimeline({
  steps,
  firstError,
  highlightedSteps,
  selectedStep,
  onSelectStep,
}: Props) {
  return (
    <ol className="timeline" aria-label="Trajectory steps">
      {steps.map((step) => {
        const isFirstError = firstError?.location === "located" && firstError.step_id === step.step_id;
        const classes = [
          "step",
          `step-${step.source}`,
          highlightedSteps.has(step.step_id) ? "step-cited" : "",
          selectedStep === step.step_id ? "step-selected" : "",
          isFirstError ? "step-first-error" : "",
        ]
          .filter(Boolean)
          .join(" ");
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
            </button>
            <p className="step-message">{textOf(step.message)}</p>
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
                <pre className="tool-call-args">{JSON.stringify(call.arguments, null, 2)}</pre>
                {(step.observation?.results ?? [])
                  .filter((result) => result.source_call_id === call.tool_call_id)
                  .map((result, index) => (
                    <pre className="observation" key={index} aria-label="Observation">
                      {textOf(result.content)}
                    </pre>
                  ))}
              </div>
            ))}
          </li>
        );
      })}
    </ol>
  );
}
