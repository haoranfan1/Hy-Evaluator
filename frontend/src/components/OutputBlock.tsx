import { useState } from "react";

import { textOf } from "../api";

// Reviewer-facing rendering for command and observation content. Real runs
// carry multi-line shell commands and observations shaped as
// {"returncode": N, "output": "..."} — often thousands of characters. The
// review protocol needs all of it *available*, but a labeling session must not
// drown in it: structured results render as an exit-code chip plus clean text,
// and long bodies collapse to a head/tail preview with an explicit hidden-line
// count. Nothing is truncated for good — expansion always shows the verbatim
// content.

export const COLLAPSE_LINE_THRESHOLD = 14;
export const PREVIEW_HEAD_LINES = 8;
export const PREVIEW_TAIL_LINES = 4;

export type ParsedObservation = {
  returncode: number | null;
  body: string;
};

export function parseObservation(content: string | unknown[] | null | undefined): ParsedObservation {
  const text = textOf(content);
  try {
    const payload: unknown = JSON.parse(text);
    if (
      payload !== null &&
      typeof payload === "object" &&
      !Array.isArray(payload) &&
      typeof (payload as { returncode?: unknown }).returncode === "number" &&
      typeof (payload as { output?: unknown }).output === "string"
    ) {
      return {
        returncode: (payload as { returncode: number }).returncode,
        body: (payload as { output: string }).output,
      };
    }
  } catch {
    // Not JSON — render the raw text unchanged.
  }
  return { returncode: null, body: text };
}

export function commandTextOf(args: Record<string, unknown>): string | null {
  const keys = Object.keys(args);
  if (keys.length === 1 && keys[0] === "command" && typeof args.command === "string") {
    return args.command;
  }
  return null;
}

function CollapsibleBody({
  text,
  label,
  className,
}: {
  text: string;
  label: string;
  className: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const lines = text.split("\n");
  const collapsible = lines.length > COLLAPSE_LINE_THRESHOLD;

  if (!collapsible) {
    return (
      <pre className={className} aria-label={label}>
        {text}
      </pre>
    );
  }
  if (expanded) {
    return (
      <div className="output-block">
        <pre className={className} aria-label={label}>
          {text}
        </pre>
        <button type="button" className="output-toggle" onClick={() => setExpanded(false)}>
          Collapse to preview
        </button>
      </div>
    );
  }
  const hidden = lines.length - PREVIEW_HEAD_LINES - PREVIEW_TAIL_LINES;
  return (
    <div className="output-block">
      <pre className={className} aria-label={label}>
        {lines.slice(0, PREVIEW_HEAD_LINES).join("\n")}
      </pre>
      <button type="button" className="output-toggle" onClick={() => setExpanded(true)}>
        Show {hidden} hidden {hidden === 1 ? "line" : "lines"} ({text.length.toLocaleString()}{" "}
        chars total)
      </button>
      <pre className={`${className} output-tail`} aria-hidden="true">
        {lines.slice(-PREVIEW_TAIL_LINES).join("\n")}
      </pre>
    </div>
  );
}

export function CommandBlock({ args }: { args: Record<string, unknown> }) {
  const command = commandTextOf(args);
  if (command !== null) {
    return <CollapsibleBody text={command} label="Command" className="tool-call-args" />;
  }
  return (
    <CollapsibleBody
      text={JSON.stringify(args, null, 2)}
      label="Tool arguments"
      className="tool-call-args"
    />
  );
}

export function ObservationBlock({ content }: { content: string | unknown[] | null | undefined }) {
  const { returncode, body } = parseObservation(content);
  const trimmed = body.replace(/\s+$/, "");
  return (
    <div className="observation" aria-label="Observation">
      {returncode !== null && (
        <p className="observation-head">
          <span className={`chip ${returncode === 0 ? "chip-pass" : "chip-fail"}`}>
            exit {returncode}
          </span>
          {trimmed === "" && <span className="observation-empty">no output</span>}
        </p>
      )}
      {trimmed !== "" && (
        <CollapsibleBody text={trimmed} label="Observation output" className="observation-body" />
      )}
      {returncode === null && trimmed === "" && <p className="observation-empty">no output</p>}
    </div>
  );
}

// Long prose summaries (a v1-era protected-path check enumerates dozens of
// tool-call references) drown the banner and evidence cards; clamp them with
// an explicit toggle instead of scrolling walls of text.
export const CLAMP_CHAR_THRESHOLD = 320;

export function ClampedText({
  text,
  className,
  threshold = CLAMP_CHAR_THRESHOLD,
}: {
  text: string;
  className: string;
  threshold?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  if (text.length <= threshold) {
    return <p className={className}>{text}</p>;
  }
  return (
    <p className={className}>
      {expanded ? text : `${text.slice(0, threshold - 20).trimEnd()}…`}{" "}
      <button type="button" className="clamp-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? "show less" : `show all (${text.length.toLocaleString()} chars)`}
      </button>
    </p>
  );
}
