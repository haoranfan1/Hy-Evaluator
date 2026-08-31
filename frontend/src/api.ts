// Typed client for the workbench API. Shapes mirror the backend contracts.

export type OutcomeStatus = "resolved" | "unresolved" | "inconclusive";
export type ProcessStatus = "valid" | "invalid" | "inconclusive";

export type EvidenceReference =
  | { kind: "atif_step"; step_id: number; tool_call_id: string | null }
  | { kind: "patch"; file: string; line: number | null }
  | { kind: "verifier"; artifact_id: string; test_name: string | null }
  | { kind: "task"; field: string };

export type FirstError = {
  location: "located" | "none" | "unlocatable";
  step_id: number | null;
  tool_call_id: string | null;
  primary_category: string | null;
};

export type DeterministicCheck = {
  check_id: string;
  status: "pass" | "fail" | "warning" | "unknown";
  summary: string;
  evidence: EvidenceReference[];
  hard_process_failure: boolean;
};

export type Finding = {
  finding_id: string;
  source: "deterministic" | "semantic" | "human";
  category: string;
  severity: "info" | "warning" | "error" | "critical";
  summary: string;
  explanation: string;
  feedback: string;
  step_id: number | null;
  tool_call_id: string | null;
  evidence: EvidenceReference[];
  downstream_step_ids: number[];
  evidence_strength: "strong" | "moderate" | "weak";
};

export type Evaluation = {
  evaluation_id: string;
  run_id: string;
  status: "completed" | "partial" | "inconclusive" | "failed";
  outcome_status: OutcomeStatus;
  process_status: ProcessStatus;
  correct_result_invalid_process: boolean | null;
  first_error: FirstError;
  deterministic_checks: DeterministicCheck[];
  findings: Finding[];
  exclusions: string[];
};

export type RunSummary = {
  run_id: string;
  task_id: string;
  repository: string;
  difficulty: string;
  run_status: string;
  outcome_status: OutcomeStatus | null;
  process_status: ProcessStatus | null;
  first_error: FirstError | null;
  evaluation_id: string | null;
  review_count: number;
};

export type TaskDetail = {
  task_id: string;
  repository: string;
  problem_statement: string;
  difficulty: { label: string; source: string };
  standard_answer: { fail_to_pass: string[]; pass_to_pass: string[] };
  protected_paths: string[];
};

export type RunRecordSummary = {
  run_id: string;
  task_id: string;
  status: string;
  agent: { name: string; version: string };
  harness: { name: string; version: string };
};

export type ArtifactTexts = {
  patch: string | null;
  test_output: string | null;
  run_log: string | null;
};

export type RunDetail = {
  run: RunRecordSummary;
  task: TaskDetail;
  evaluation: Evaluation | null;
  artifacts: ArtifactTexts;
};

export type ToolCall = {
  tool_call_id: string;
  function_name: string;
  arguments: Record<string, unknown>;
};

export type ObservationResult = {
  source_call_id: string | null;
  content: string | unknown[] | null;
};

export type TrajectoryStep = {
  step_id: number;
  source: "system" | "user" | "agent";
  message: string | unknown[];
  reasoning_content?: string | null;
  tool_calls?: ToolCall[] | null;
  observation?: { results: ObservationResult[] } | null;
};

export type Trajectory = {
  schema_version: string;
  session_id?: string | null;
  steps: TrajectoryStep[];
};

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} failed with status ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

export function fetchRuns(): Promise<{ runs: RunSummary[] }> {
  return getJson("/api/runs");
}

export function fetchRunDetail(runId: string): Promise<RunDetail> {
  return getJson(`/api/runs/${encodeURIComponent(runId)}`);
}

export function fetchTrajectory(runId: string): Promise<Trajectory> {
  return getJson(`/api/runs/${encodeURIComponent(runId)}/trajectory`);
}

export function textOf(value: string | unknown[] | null | undefined): string {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value
      .map((part) =>
        part && typeof part === "object" && "text" in part ? String((part as { text: unknown }).text) : "",
      )
      .join("\n");
  }
  return "";
}

export function citedStepIds(evidence: EvidenceReference[]): Set<number> {
  const ids = new Set<number>();
  for (const reference of evidence) {
    if (reference.kind === "atif_step") {
      ids.add(reference.step_id);
    }
  }
  return ids;
}
