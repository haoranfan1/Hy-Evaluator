// Human-readable run names. A run id is the Harbor trial name reused verbatim
// (SWE-bench instance id + random trial suffix + agent role), which is stable
// and unique but hard to read. The short form is presentation only: every
// link, record, and export still uses the full id.

export type RunName = {
  short: string;
  full: string;
  kind: "swebench" | "fixture" | "other";
  trial: string | null;
};

const SWEBENCH_TRIAL = /^([A-Za-z0-9.-]+)__([A-Za-z0-9.-]+)-(\d+)__([A-Za-z0-9]+)__([A-Za-z0-9-]+)$/;
const FIXTURE = /^run-fixture-(.+)$/;

// Short names for a list of runs. Two runs of the same task (a baseline and a
// rerun) would collide on the short form, so those get their trial suffix back.
export function runShortNames(runIds: string[]): Map<string, string> {
  const names = runIds.map((id) => [id, runDisplayName(id)] as const);
  const counts = new Map<string, number>();
  for (const [, name] of names) {
    counts.set(name.short, (counts.get(name.short) ?? 0) + 1);
  }
  return new Map(
    names.map(([id, name]) => [
      id,
      (counts.get(name.short) ?? 0) > 1 && name.trial ? `${name.short} · ${name.trial}` : name.short,
    ]),
  );
}

export function runDisplayName(runId: string): RunName {
  const trial = SWEBENCH_TRIAL.exec(runId);
  if (trial) {
    const [, , repo, number, suffix] = trial;
    return { short: `${repo}-${number}`, full: runId, kind: "swebench", trial: suffix };
  }
  if (FIXTURE.test(runId)) {
    // Fixture ids are already readable; keep them verbatim.
    return { short: runId, full: runId, kind: "fixture", trial: null };
  }
  return { short: runId, full: runId, kind: "other", trial: null };
}
