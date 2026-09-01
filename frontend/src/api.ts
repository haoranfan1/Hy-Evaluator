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

export type HumanLabel = {
  process_status: ProcessStatus;
  first_error_location: "located" | "none" | "unlocatable";
  first_error_step_id: number | null;
  primary_category: string | null;
  notes: string;
};

export type FindingDecision = {
  finding_id: string;
  decision: "accept" | "edit" | "reject" | "needs_more_evidence";
  notes: string;
};

export type HumanReview = {
  review_id: string;
  evaluation_id: string;
  review_version: number;
  reviewer_alias: string;
  rubric_version: string;
  initial_label: HumanLabel;
  evaluator_revealed_at: string | null;
  adjudication: "accept" | "edit" | "reject" | "needs_more_evidence" | null;
  final_label: HumanLabel | null;
  finding_decisions: FindingDecision[];
  notes: string;
};

export type RunDetail = {
  run: RunRecordSummary;
  task: TaskDetail;
  evaluation: Evaluation | null;
  reviews: HumanReview[];
  artifacts: ArtifactTexts;
};

export type MetricValue = {
  metric_id: string;
  value: number | null;
  numerator: number;
  denominator: number;
  provenance: string;
  definition: string;
  exclusions: string[];
};

export type AnalyticsSummary = {
  run_count: number;
  evaluated_count: number;
  reviewed_count: number;
  adjudicated_count: number;
  configuration: Record<string, string | number>;
  metrics: MetricValue[];
  primary_error_distribution: {
    category: string;
    count: number;
    human_count: number;
    evaluator_count: number;
  }[];
  difficulty_table: {
    label: string;
    total_runs: number;
    gradeable_runs: number;
    resolved_runs: number;
    outcome_rate: number | null;
    process_gradeable_runs: number;
    process_valid_runs: number;
    process_valid_rate: number | null;
    inconclusive_runs: number;
    provenance: string;
  }[];
  quadrant: {
    outcome_status: string;
    process_status: string;
    run_ids: string[];
    provenance: string;
  }[];
  observed_decline_interval: string;
  statistically_supported_decline_interval: string;
  excluded_runs: { run_id: string; reasons: string[] }[];
  cases: {
    run_id: string;
    evaluation_id: string | null;
    kind: string;
    note: string;
    adjudication: string | null;
  }[];
};

export type ScoreCount = { runs: string[]; n: number; d: number };

export type RegressionLane = {
  evaluator_version: string;
  status: string;
  process_status: string;
  first_error_step: number | null;
};

export type RegressionRun = {
  run_id: string;
  task_id: string;
  human: { process_status: string; first_error_step: number | null };
  stored: RegressionLane;
  reevaluated: RegressionLane & {
    exclusions: string[];
    semantic_condensation: string | null;
    protected_check: { status: string; summary: string } | null;
  };
};

export type RegressionCard = {
  schema_version: string;
  recorded_at: string;
  slice_id: string;
  note: string;
  stored_version: string;
  reevaluated_version: string;
  scores: Record<string, Record<string, ScoreCount>>;
  runs: RegressionRun[];
};

export type JudgeStabilityRecord = {
  schema_version: string;
  recorded_at: string;
  subject: string;
  repeats: number;
  judge: {
    model: string;
    reasoning_effort: string;
    temperature: number;
    top_p: number;
    rubric_version: string;
    semantic_prompt_version: string;
  };
  summary: {
    completed: number;
    verdict_unanimous: boolean;
    verdicts: string[];
    first_error_steps: number[];
    step_unanimous: boolean;
  };
  attempts: {
    attempt: number;
    status: string;
    process_status: string | null;
    first_error_location: string | null;
    first_error_step: number | null;
    primary_category: string | null;
    finding_count: number | null;
    repair_retries: number | null;
  }[];
};

export type ValidationRecords = {
  regression_cards: { file: string; card: RegressionCard }[];
  judge_stability: { file: string; record: JudgeStabilityRecord }[];
  unreadable: { file: string; reason: string }[];
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

export function fetchValidationRecords(): Promise<ValidationRecords> {
  return getJson("/api/regressions");
}

export function fetchAnalytics(scope?: string): Promise<AnalyticsSummary> {
  const query = scope ? `?scope=${encodeURIComponent(scope)}` : "";
  return getJson(`/api/analytics/summary${query}`);
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      // keep the status code as the message
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function postInitialReview(
  evaluationId: string,
  body: {
    reviewer_alias: string;
    rubric_version: string;
    initial_label: HumanLabel;
    notes?: string;
  },
): Promise<HumanReview> {
  return postJson(`/api/evaluations/${encodeURIComponent(evaluationId)}/initial-review`, body);
}

export function postAdjudication(
  evaluationId: string,
  body: {
    reviewer_alias: string;
    rubric_version: string;
    adjudication: "accept" | "edit" | "reject" | "needs_more_evidence";
    final_label: HumanLabel;
    finding_decisions?: FindingDecision[];
    notes?: string;
  },
): Promise<HumanReview> {
  return postJson(`/api/evaluations/${encodeURIComponent(evaluationId)}/adjudications`, body);
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
