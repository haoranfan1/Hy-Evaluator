"""Map one completed Harbor SWE-bench trial into a workbench evidence bundle.

The importer never fabricates evidence: every artifact is copied verbatim from
the Harbor trial directory, hashed, and referenced by identity. Dataset facts
come from one pinned SWE-bench Verified row, cross-checked against the task
directory the trial actually ran, and any inconsistency rejects the trial
instead of importing a guess.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from hy3_workbench.artifact_store import ArtifactStore
from hy3_workbench.atif import AtifAdapter, AtifValidationError
from hy3_workbench.contracts import (
    AgentConfiguration,
    ArtifactReference,
    BehavioralTestContract,
    BenchmarkIdentity,
    CheckerIdentity,
    Difficulty,
    HarnessConfiguration,
    Identifier,
    ModelConfiguration,
    ReferencePatchProvenance,
    RunRecord,
    Selection,
    TaskManifest,
    TrajectoryReference,
    VerifierRecord,
)
from hy3_workbench.evidence_extractor import parse_patch
from hy3_workbench.evidence_gate import parse_verifier_report

HARBOR_DATASET_ADAPTER_VERSION = "harbor-swebench-adapter-v1"
PATCH_DUMP_MARKER = "# hy3-workbench: record the agent-authored diff before grading"

_identifier_adapter = TypeAdapter(Identifier)
_CHECKER_VERSION_PATTERN = re.compile(r"swebench==([0-9][0-9a-zA-Z.]*)")


class HarborImportError(ValueError):
    """A Harbor trial cannot be mapped into a trustworthy evidence bundle."""


@dataclass(frozen=True)
class BuiltBundle:
    """Location and identity of one importable bundle."""

    run_id: str
    bundle_dir: str


def _load_json(path: Path, description: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HarborImportError(f"{description} is unreadable: {error}") from error
    if not isinstance(payload, dict):
        raise HarborImportError(f"{description} is not a JSON object")
    return payload


def _json_list(value: object, description: str) -> list[str]:
    """Decode a dataset list field that may arrive JSON-encoded."""

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise HarborImportError(f"{description} is not valid JSON: {error}") from error
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise HarborImportError(f"{description} is not a list of test names")
    return value


def _require_str(row: dict, field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HarborImportError(f"dataset row field {field} is missing or empty")
    return value


def _parse_trial_timestamp(value: object, description: str) -> datetime:
    if not isinstance(value, str):
        raise HarborImportError(f"{description} is missing from the trial result")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise HarborImportError(f"{description} is not an ISO timestamp: {error}") from error


class HarborImporter:
    """Build a manifest/run evidence bundle from one Harbor trial."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        self.artifacts = ArtifactStore(self.project_root)
        self.atif = AtifAdapter()

    def build_bundle(
        self,
        *,
        dataset_row: dict,
        dataset_revision: str,
        dataset_source_url: str,
        task_dir: Path,
        trial_dir: Path,
        bundle_root: Path,
        selection: Selection,
        harness_version: str,
        slice_id: str | None = None,
    ) -> BuiltBundle:
        row = dict(dataset_row)
        instance_id = _require_str(row, "instance_id")
        fail_to_pass = _json_list(row.get("FAIL_TO_PASS"), "dataset FAIL_TO_PASS")
        pass_to_pass = _json_list(row.get("PASS_TO_PASS"), "dataset PASS_TO_PASS")
        self._cross_check_task_dir(task_dir, instance_id, row, fail_to_pass, pass_to_pass)

        result = _load_json(trial_dir / "result.json", "trial result.json")
        if result.get("exception_info") is not None:
            raise HarborImportError(
                f"trial recorded an exception and is not importable: {result['exception_info']}"
            )
        started_at = _parse_trial_timestamp(result.get("started_at"), "trial started_at")
        completed_at = _parse_trial_timestamp(result.get("finished_at"), "trial finished_at")

        trajectory = self._validated_trajectory(trial_dir)
        run_id = self._run_id_from_session(trajectory.session_id)

        bundle_abs = (self.project_root / bundle_root / run_id).resolve()
        if not bundle_abs.is_relative_to(self.project_root):
            raise HarborImportError("bundle_root escapes the project root")
        if bundle_abs.exists() and any(bundle_abs.iterdir()):
            raise HarborImportError(f"bundle directory already exists: {bundle_abs}")
        bundle_abs.mkdir(parents=True, exist_ok=True)
        bundle_rel = bundle_abs.relative_to(self.project_root).as_posix()

        trajectory_ref = self._copy_artifact(
            trial_dir / "agent" / "trajectory.json", bundle_abs / "trajectory.json", required=True
        )
        patch_ref = self._copy_artifact(
            trial_dir / "verifier" / "patch.diff", bundle_abs / "patch.diff", required=True
        )
        report_ref = self._copy_artifact(
            trial_dir / "verifier" / "report.json", bundle_abs / "verifier-report.json"
        )
        test_output_ref = self._copy_artifact(
            trial_dir / "verifier" / "test-stdout.txt", bundle_abs / "test-output.txt"
        )
        run_log_ref = self._copy_artifact(trial_dir / "trial.log", bundle_abs / "run.log")

        reference_patch = None
        gold_patch = row.get("patch")
        if isinstance(gold_patch, str) and gold_patch.strip():
            gold_path = bundle_abs / "reference-patch.diff"
            gold_path.write_text(gold_patch, encoding="utf-8")
            reference_patch = ReferencePatchProvenance(
                artifact=self.artifacts.register(f"{bundle_rel}/reference-patch.diff")
            )

        manifest = self._build_manifest(
            row,
            instance_id,
            fail_to_pass,
            pass_to_pass,
            dataset_revision,
            dataset_source_url,
            task_dir,
            selection,
            reference_patch,
        )
        run = RunRecord(
            run_id=run_id,
            task_id=instance_id,
            slice_id=slice_id,
            status="completed",
            model=self._model_configuration(result),
            agent=self._agent_configuration(result),
            harness=HarnessConfiguration(name="harbor", version=harness_version),
            dataset_adapter=HARBOR_DATASET_ADAPTER_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            trajectory=TrajectoryReference(
                **trajectory_ref.model_dump(), schema_version="ATIF-v1.7"
            ),
            patch=patch_ref,
            verifier=self._verifier_record(
                manifest, report_ref, test_output_ref, run_log_ref, bundle_abs
            ),
        )

        (bundle_abs / "manifest.json").write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (bundle_abs / "run.json").write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return BuiltBundle(run_id=run_id, bundle_dir=bundle_rel)

    # Cross-checks -------------------------------------------------------------

    def _cross_check_task_dir(
        self,
        task_dir: Path,
        instance_id: str,
        row: dict,
        fail_to_pass: list[str],
        pass_to_pass: list[str],
    ) -> None:
        config = _load_json(task_dir / "tests" / "config.json", "task tests/config.json")
        if config.get("instance_id") != instance_id:
            raise HarborImportError(
                "task directory instance_id does not match the dataset row: "
                f"{config.get('instance_id')} != {instance_id}"
            )
        if config.get("base_commit") != _require_str(row, "base_commit"):
            raise HarborImportError("task directory base_commit does not match the dataset row")
        task_f2p = set(_json_list(config.get("FAIL_TO_PASS"), "task FAIL_TO_PASS"))
        task_p2p = set(_json_list(config.get("PASS_TO_PASS"), "task PASS_TO_PASS"))
        if task_f2p != set(fail_to_pass) or task_p2p != set(pass_to_pass):
            raise HarborImportError(
                "task directory behavioral-test contract does not match the dataset row"
            )

    def _validated_trajectory(self, trial_dir: Path):
        trajectory_path = trial_dir / "agent" / "trajectory.json"
        if not trajectory_path.is_file():
            raise HarborImportError(
                "trial has no agent/trajectory.json ATIF trajectory; refusing to import"
            )
        try:
            trajectory = self.atif.load(trajectory_path)
        except (AtifValidationError, OSError) as error:
            raise HarborImportError(f"trial ATIF trajectory failed validation: {error}") from error
        if trajectory.schema_version != "ATIF-v1.7":
            raise HarborImportError(
                f"trial trajectory schema is {trajectory.schema_version}, expected ATIF-v1.7"
            )
        return trajectory

    @staticmethod
    def _run_id_from_session(session_id: str) -> str:
        try:
            return _identifier_adapter.validate_python(session_id)
        except ValidationError as error:
            raise HarborImportError(
                f"trajectory session_id is not a usable run identifier: {session_id!r}"
            ) from error

    # Artifact handling --------------------------------------------------------

    def _copy_artifact(
        self, source: Path, destination: Path, *, required: bool = False
    ) -> ArtifactReference | None:
        if not source.is_file():
            if required:
                raise HarborImportError(f"required trial artifact is missing: {source}")
            return None
        shutil.copyfile(source, destination)
        relative = destination.relative_to(self.project_root).as_posix()
        return self.artifacts.register(relative)

    # Record construction ------------------------------------------------------

    def _build_manifest(
        self,
        row: dict,
        instance_id: str,
        fail_to_pass: list[str],
        pass_to_pass: list[str],
        dataset_revision: str,
        dataset_source_url: str,
        task_dir: Path,
        selection: Selection,
        reference_patch: ReferencePatchProvenance | None,
    ) -> TaskManifest:
        repository = _require_str(row, "repo")
        pr_number = instance_id.rsplit("-", 1)[-1]
        if not pr_number.isdigit():
            raise HarborImportError(f"instance_id has no trailing PR number: {instance_id}")
        # SWE-bench instances are built from the upstream pull request whose
        # number ends the instance id; the dataset carries no separate issue
        # link, so both source fields point at that canonical PR.
        pr_url = f"https://github.com/{repository}/pull/{pr_number}"

        protected = sorted(
            {file.path for file in parse_patch(_require_str(row, "test_patch")).files}
        )
        if not protected:
            raise HarborImportError("dataset test_patch declares no protected test files")

        return TaskManifest(
            task_id=instance_id,
            benchmark=BenchmarkIdentity(
                name="SWE-bench Verified",
                revision=dataset_revision,
                source_url=dataset_source_url,
            ),
            repository=repository,
            base_commit=_require_str(row, "base_commit"),
            problem_statement=_require_str(row, "problem_statement"),
            source_issue_url=pr_url,
            source_pr_url=pr_url,
            standard_answer=BehavioralTestContract(
                kind="behavioral_test_contract",
                fail_to_pass=fail_to_pass,
                pass_to_pass=pass_to_pass,
            ),
            checker=CheckerIdentity(
                adapter="swebench-official-grading",
                version=self._checker_version(task_dir),
            ),
            difficulty=Difficulty(
                label=_require_str(row, "difficulty"),
                source="SWE-bench Verified difficulty annotation",
            ),
            selection=selection,
            protected_paths=protected,
            # The graded test files are public repository content; reading
            # them is legitimate investigation and only modification violates
            # process integrity.
            protected_path_policy="no_modify",
            reference_patch=reference_patch,
        )

    @staticmethod
    def _checker_version(task_dir: Path) -> str:
        try:
            test_script = (task_dir / "tests" / "test.sh").read_text(encoding="utf-8")
        except OSError as error:
            raise HarborImportError(f"task tests/test.sh is unreadable: {error}") from error
        match = _CHECKER_VERSION_PATTERN.search(test_script)
        if match is None:
            raise HarborImportError("task tests/test.sh does not pin a swebench grader version")
        return match.group(1)

    @staticmethod
    def _model_configuration(result: dict) -> ModelConfiguration:
        config = result.get("config")
        agent_config = config.get("agent") if isinstance(config, dict) else None
        if not isinstance(agent_config, dict):
            raise HarborImportError("trial result has no agent configuration block")
        model_name = agent_config.get("model_name")
        if not isinstance(model_name, str) or not model_name:
            raise HarborImportError("trial agent configuration records no model name")
        kwargs = agent_config.get("kwargs") if isinstance(agent_config.get("kwargs"), dict) else {}
        temperature = kwargs.get("temperature")
        top_p = kwargs.get("top_p")
        return ModelConfiguration(
            name=model_name,
            endpoint_kind="openai-compatible",
            reasoning_effort=kwargs.get("reasoning_effort"),
            temperature=temperature if isinstance(temperature, int | float) else None,
            top_p=top_p if isinstance(top_p, int | float) else None,
        )

    @staticmethod
    def _agent_configuration(result: dict) -> AgentConfiguration:
        agent_info = result.get("agent_info")
        if not isinstance(agent_info, dict) or not isinstance(agent_info.get("name"), str):
            raise HarborImportError("trial result has no agent_info identity")
        config = result.get("config")
        agent_config = config.get("agent") if isinstance(config, dict) else {}
        digest = hashlib.sha256(
            json.dumps(agent_config, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        version = agent_info.get("version")
        return AgentConfiguration(
            name=agent_info["name"],
            version=version if isinstance(version, str) and version else "unknown",
            config_digest=digest,
        )

    def _verifier_record(
        self,
        manifest: TaskManifest,
        report_ref: ArtifactReference | None,
        test_output_ref: ArtifactReference | None,
        run_log_ref: ArtifactReference | None,
        bundle_abs: Path,
    ) -> VerifierRecord:
        if report_ref is None:
            return VerifierRecord(
                status="inconclusive",
                report=None,
                test_output=test_output_ref,
                run_log=run_log_ref,
                exclusion_reason=(
                    "the trial produced no official verifier report.json, so the outcome "
                    "cannot be graded"
                ),
            )
        try:
            payload = json.loads((bundle_abs / "verifier-report.json").read_text(encoding="utf-8"))
            report = parse_verifier_report(payload)
        except ValueError as error:
            return VerifierRecord(
                status="inconclusive",
                report=report_ref,
                test_output=test_output_ref,
                run_log=run_log_ref,
                exclusion_reason=f"the official verifier report is not gradeable: {error}",
            )
        results = [*report.fail_to_pass, *report.pass_to_pass]
        derived = "resolved" if all(r.status == "passed" for r in results) else "unresolved"
        if report.outcome_status != derived:
            raise HarborImportError(
                "official verifier report resolved flag contradicts its per-test results"
            )
        declared = set(manifest.standard_answer.fail_to_pass) | set(
            manifest.standard_answer.pass_to_pass
        )
        reported = {r.name for r in results}
        if reported != declared:
            raise HarborImportError(
                "official verifier report does not cover the declared behavioral tests: "
                f"missing={sorted(declared - reported)} undeclared={sorted(reported - declared)}"
            )
        return VerifierRecord(
            status="passed" if derived == "resolved" else "failed",
            report=report_ref,
            test_output=test_output_ref,
            run_log=run_log_ref,
            exclusion_reason=None,
        )


# Task preparation ------------------------------------------------------------


def rewrite_dockerfile_from(dockerfile_text: str, replacement_image: str) -> tuple[str, str]:
    """Replace the single FROM line with a locally built image reference.

    Returns the rewritten text and the original image so provenance can record
    exactly what was swapped.
    """

    lines = dockerfile_text.splitlines()
    from_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip().upper().startswith("FROM ") and not line.lstrip().startswith("#")
    ]
    if len(from_indexes) != 1:
        raise HarborImportError(
            f"expected exactly one FROM line in the task Dockerfile, found {len(from_indexes)}"
        )
    index = from_indexes[0]
    original_image = lines[index].strip().split(None, 1)[1]
    lines[index] = f"FROM {replacement_image}"
    return "\n".join(lines) + "\n", original_image


def inject_patch_dump(test_script_text: str) -> str:
    """Record the agent-authored working-tree diff before the grader mutates it.

    The dump runs immediately after the script enters /testbed and before the
    official flow resets test files, so test tampering by the agent stays
    visible to the protected-path check.
    """

    if PATCH_DUMP_MARKER in test_script_text:
        raise HarborImportError("test.sh already contains the patch dump block")
    lines = test_script_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "cd /testbed":
            indent = line[: len(line) - len(line.lstrip())]
            block = [
                f"{indent}{PATCH_DUMP_MARKER}",
                f"{indent}mkdir -p /logs/verifier",
                f"{indent}git add -N . 2>/dev/null || true",
                f"{indent}git diff HEAD > /logs/verifier/patch.diff 2>/dev/null || true",
                f"{indent}git reset --quiet 2>/dev/null || true",
            ]
            lines[index + 1 : index + 1] = block
            return "\n".join(lines) + "\n"
    raise HarborImportError("test.sh has no 'cd /testbed' line to anchor the patch dump")
