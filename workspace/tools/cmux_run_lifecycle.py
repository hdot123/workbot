#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if __package__ in {None, ""} and str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.current_task_source import (
    ARCHIVE_ONLY_STATUS,
    build_main_thread_task_source_ref,
    maybe_normalize_task_source_ref,
)

LOCAL_TZ = timezone(timedelta(hours=8))

DEFAULT_S01_FILES = (
    "execution-log.md",
    "scope-and-targets.md",
    "unresolved-items.md",
    "permission-mode-trace.md",
    "control-packet-trace.md",
    "a7-finish-trace.md",
    "test-plan.md",
)


@dataclass(frozen=True)
class DigestRecord:
    kind: str
    path: Path
    digest: str


def resolve_paths(paths: Iterable[Path] | None) -> tuple[Path, ...]:
    return tuple(paths or ())


def now_text() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def render_header(step_id: str, step_name: str, run_id: str, timestamp: str) -> str:
    return (
        f"StepId: {step_id}\n"
        f"StepName: {step_name}\n"
        f"RunId: {run_id}\n"
        f"Timestamp: {timestamp}\n\n"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_path(path: Path) -> str:
    target = path.expanduser().resolve()
    if not target.exists():
        return "MISSING"
    if target.is_file():
        return sha256_file(target)
    if target.is_dir():
        digest = hashlib.sha256()
        for current in sorted(target.rglob("*")):
            relative = current.relative_to(target).as_posix()
            if current.is_dir():
                digest.update(f"dir:{relative}\n".encode("utf-8"))
                continue
            digest.update(f"file:{relative}\n".encode("utf-8"))
            digest.update(sha256_file(current).encode("ascii"))
            digest.update(b"\n")
        return digest.hexdigest()
    return "UNSUPPORTED"


def collect_records(paths: Iterable[Path], kind: str) -> list[DigestRecord]:
    return [DigestRecord(kind=kind, path=path.expanduser().resolve(), digest=digest_path(path)) for path in paths]


def parse_baseline_records(rendered: str) -> dict[Path, str]:
    records: dict[Path, str] = {}
    for line in rendered.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("ProtectedFile::") or stripped.startswith("ProtectedDir::"):
            _, raw_path, digest = stripped.split("::", 2)
            records[Path(raw_path).resolve()] = digest.strip()
            continue
        if "  /" in stripped and len(stripped.split()) >= 2:
            digest, raw_path = stripped.split(None, 1)
            records[Path(raw_path).resolve()] = digest.strip()
            continue
        if "|" in stripped and stripped.startswith("/"):
            raw_path, digest = [part.strip() for part in stripped.split("|", 1)]
            records[Path(raw_path).resolve()] = digest
    return records


def git_status_lines(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"failed to collect git status from {repo_root}: {exc.stderr}") from exc
    return [line.rstrip() for line in result.stdout.splitlines()]


def relative_to_repo(repo_root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def filter_run_dir_status(lines: Iterable[str], run_dir_relative: str | None) -> list[str]:
    if not run_dir_relative:
        return [line for line in lines]
    filtered: list[str] = []
    needle = f"{run_dir_relative}/"
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if run_dir_relative in stripped or needle in stripped:
            continue
        filtered.append(line)
    return filtered


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def resolve_main_thread_task_source_ref(
    *,
    run_id: str,
    run_dir: Path,
    task_source_ref: dict[str, object] | None,
) -> dict[str, str]:
    if task_source_ref is not None:
        normalized = maybe_normalize_task_source_ref(task_source_ref, expected_task_type="main_thread")
        if normalized is None:  # pragma: no cover - defensive
            raise RuntimeError("task_source_ref normalization returned None")
        return normalized
    return build_main_thread_task_source_ref(
        request_id=run_id,
        deliverable_path=str(run_dir),
        evidence_path=str(run_dir),
        status="initialized",
        acceptance_owner="main-thread",
    )


def initialize_run(
    *,
    run_dir: Path,
    run_id: str,
    task_source_ref: dict[str, object] | None = None,
    repo_root: Path = REPO_ROOT,
    protected_files: Iterable[Path] | None = None,
    protected_dirs: Iterable[Path] | None = None,
    external_paths: Iterable[Path] | None = None,
) -> list[Path]:
    timestamp = now_text()
    run_dir = run_dir.expanduser().resolve()
    protected_files = resolve_paths(protected_files)
    protected_dirs = resolve_paths(protected_dirs)
    external_paths = resolve_paths(external_paths)
    run_dir.mkdir(parents=True, exist_ok=False)
    run_dir_relative = relative_to_repo(repo_root, run_dir)
    normalized_task_source_ref = resolve_main_thread_task_source_ref(
        run_id=run_id,
        run_dir=run_dir,
        task_source_ref=task_source_ref,
    )

    created: list[Path] = []
    created.append(write_json(run_dir / "current-task-source.json", normalized_task_source_ref))

    protected_records = collect_records(protected_files, "file") + collect_records(protected_dirs, "dir")
    protected_lines = [
        "# Protected Files Baseline",
        "",
        f"- Timestamp: {timestamp}",
        f"- Run dir: {run_dir}",
        "",
    ]
    for record in protected_records:
        label = "ProtectedFile" if record.kind == "file" else "ProtectedDir"
        protected_lines.append(f"{label}::{record.path}::{record.digest}")
    created.append(
        write_text(
            run_dir / "protected-files-baseline.txt",
            "\n".join(protected_lines) + "\n",
        )
    )

    external_records = collect_records(external_paths, "external")
    external_lines = [
        "# External Protected Check",
        "",
        render_header("S01", "Initialize Run", run_id, timestamp).rstrip(),
        "",
        "ExternalReadAttempted: no",
        "ExternalReadPaths: none",
        "ExternalWriteAttempted: no",
        "ExternalWritePaths: none",
        "CheckedCommands: none",
        "CheckedArtifacts: none",
        "StartResult: PASS",
        "EndResult: pending",
        "",
        "## Baseline digests",
    ]
    for record in external_records:
        external_lines.append(f"{record.path} | {record.digest}")
    created.append(write_text(run_dir / "external-protected-check.md", "\n".join(external_lines) + "\n"))

    initial_status = git_status_lines(repo_root)
    manifest_lines = [
        "# Repo Change Manifest",
        "",
        render_header("S01", "Initialize Run", run_id, timestamp).rstrip(),
        "",
        f"RepoRoot: {repo_root.resolve()}",
        f"RunDir: {run_dir}",
        f"RunDirRepoRelative: {run_dir_relative or 'OUTSIDE_REPO'}",
        "RunDirRepoRelativeExempt: yes",
        "RepoChangeManifestStatus: baseline-recorded",
        "",
        "## Initial Git Status",
        "```text",
        *initial_status,
        "```",
    ]
    created.append(write_text(run_dir / "repo-change-manifest.md", "\n".join(manifest_lines) + "\n"))

    placeholders = {
        "execution-log.md": (
            "# Execution Log\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "RunStatus: initialized\n"
            + f"RunDir: {run_dir}\n"
        ),
        "scope-and-targets.md": (
            "# Scope And Targets\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "ScopeStatus: pending\n"
        ),
        "unresolved-items.md": (
            "# Unresolved Items\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "CurrentStatus: pending root-cause trace\n"
        ),
        "permission-mode-trace.md": (
            "# Permission Mode Trace\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "TraceStatus: not started\n"
        ),
        "control-packet-trace.md": (
            "# Control Packet Trace\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "TraceStatus: not started\n"
        ),
        "a7-finish-trace.md": (
            "# A7 Finish Trace\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "TraceStatus: not started\n"
        ),
        "test-plan.md": (
            "# Test Plan\n\n"
            + render_header("S01", "Initialize Run", run_id, timestamp)
            + "TestPlanStatus: pending\n"
        ),
    }
    for name, content in placeholders.items():
        created.append(write_text(run_dir / name, content))
    return created


def compare_records(expected: dict[Path, str], current_paths: Iterable[Path]) -> tuple[str, list[str]]:
    current = {path.expanduser().resolve(): digest_path(path) for path in current_paths}
    lines: list[str] = []
    dirty = False
    all_paths = sorted(set(expected) | set(current), key=lambda item: str(item))
    for path in all_paths:
        baseline = expected.get(path, "MISSING")
        current_digest = current.get(path, "MISSING")
        changed = baseline != current_digest
        if changed:
            dirty = True
        lines.append(
            f"{path} | baseline={baseline} | current={current_digest} | changed={'yes' if changed else 'no'}"
        )
    return ("dirty" if dirty else "clean"), lines


def parse_initial_status_block(rendered: str) -> list[str]:
    marker = "## Initial Git Status"
    if marker not in rendered:
        return []
    _, _, tail = rendered.partition(marker)
    if "```text" not in tail:
        return []
    _, _, block = tail.partition("```text")
    block, _, _ = block.partition("```")
    return [line.rstrip() for line in block.splitlines() if line.rstrip()]


def ensure_placeholder(path: Path, title: str, step_id: str, step_name: str, run_id: str, timestamp: str, body: str) -> None:
    if path.exists():
        return
    write_text(path, f"# {title}\n\n{render_header(step_id, step_name, run_id, timestamp)}{body}")


def finalize_reject(
    *,
    run_dir: Path,
    run_id: str,
    reason: str,
    task_source_ref: dict[str, object] | None = None,
    repo_root: Path = REPO_ROOT,
    protected_files: Iterable[Path] | None = None,
    protected_dirs: Iterable[Path] | None = None,
    external_paths: Iterable[Path] | None = None,
) -> list[Path]:
    timestamp = now_text()
    run_dir = run_dir.expanduser().resolve()
    protected_files = resolve_paths(protected_files)
    protected_dirs = resolve_paths(protected_dirs)
    external_paths = resolve_paths(external_paths)
    run_dir.mkdir(parents=True, exist_ok=True)

    created_or_updated: list[Path] = []
    run_dir_relative = relative_to_repo(repo_root, run_dir)
    task_source_path = run_dir / "current-task-source.json"
    if task_source_path.exists():
        normalized_task_source_ref = maybe_normalize_task_source_ref(
            json.loads(task_source_path.read_text(encoding="utf-8")),
            expected_task_type="main_thread",
            allow_archive_only=True,
        )
    else:
        normalized_task_source_ref = resolve_main_thread_task_source_ref(
            run_id=run_id,
            run_dir=run_dir,
            task_source_ref=task_source_ref,
        )
    archive_only_ref = dict(normalized_task_source_ref or {})
    archive_only_ref["status"] = ARCHIVE_ONLY_STATUS
    archive_only_ref["closure_reason"] = reason
    created_or_updated.append(write_json(task_source_path, archive_only_ref))

    unresolved = run_dir / "unresolved-items.md"
    ensure_placeholder(
        unresolved,
        "Unresolved Items",
        "S08",
        "Unified Reject Closure",
        run_id,
        timestamp,
        "CurrentStatus: reject closure synthesized by helper\n",
    )
    unresolved_text = unresolved.read_text(encoding="utf-8").rstrip() + (
        f"\n\nFinalRejectReason: {reason}\nFinalRejectAt: {timestamp}\n"
    )
    created_or_updated.append(write_text(unresolved, unresolved_text + "\n"))

    baseline_path = run_dir / "protected-files-baseline.txt"
    baseline_records = parse_baseline_records(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    if not baseline_records:
        bootstrap_records = collect_records(protected_files, "file") + collect_records(protected_dirs, "dir")
        baseline_records = {record.path: record.digest for record in bootstrap_records}
        baseline_lines = [
            "# Protected Files Baseline",
            "",
            f"- Timestamp: {timestamp}",
            f"- Run dir: {run_dir}",
            "",
        ]
        for record in bootstrap_records:
            label = "ProtectedFile" if record.kind == "file" else "ProtectedDir"
            baseline_lines.append(f"{label}::{record.path}::{record.digest}")
        created_or_updated.append(write_text(baseline_path, "\n".join(baseline_lines) + "\n"))
    protected_status, protected_lines = compare_records(
        baseline_records,
        list(protected_files) + list(protected_dirs),
    )
    protected_diff = (
        "# Protected Files Diff\n\n"
        + render_header("S08", "Unified Reject Closure", run_id, timestamp)
        + f"ProtectedDiffStatus: {protected_status}\n\n"
        + "\n".join(protected_lines)
        + "\n"
    )
    created_or_updated.append(write_text(run_dir / "protected-files-diff.txt", protected_diff))

    external_records = collect_records(external_paths, "external")
    external_changes = [record for record in external_records if record.digest == "MISSING"]
    external_check = run_dir / "external-protected-check.md"
    existing_external = external_check.read_text(encoding="utf-8").rstrip() if external_check.exists() else "# External Protected Check"
    external_append = [
        "",
        "## Final Status",
        render_header("S08", "Unified Reject Closure", run_id, timestamp).rstrip(),
        "ExternalReadAttempted: unknown",
        "ExternalReadPaths: unknown",
        "ExternalWriteAttempted: no",
        "ExternalWritePaths: none",
        "CheckedCommands: helper reject closure",
        "CheckedArtifacts: external-protected-check.md, protected-files-diff.txt, repo-change-manifest.md, final-summary.md",
        f"EndResult: {'FAIL' if external_changes else 'PASS'}",
    ]
    for record in external_records:
        external_append.append(f"{record.path} | current_digest={record.digest}")
    created_or_updated.append(write_text(external_check, existing_external + "\n" + "\n".join(external_append) + "\n"))

    manifest_path = run_dir / "repo-change-manifest.md"
    current_status_lines = git_status_lines(repo_root)
    filtered_current = filter_run_dir_status(current_status_lines, run_dir_relative)
    existing_manifest = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    initial_status_lines = parse_initial_status_block(existing_manifest)
    filtered_initial = filter_run_dir_status(initial_status_lines, run_dir_relative)
    manifest_status = "exact" if filtered_current == filtered_initial else "changed"
    leak_status = "no"
    manifest_append = [
        "",
        "## Final Status",
        render_header("S08", "Unified Reject Closure", run_id, timestamp).rstrip(),
        f"RepoChangeManifestStatus: {manifest_status}",
        "RunArtifactLeakExemptPath: " + (run_dir_relative or "OUTSIDE_REPO"),
        f"ArtifactLeakInRepoTruthPaths: {leak_status}",
        "",
        "### Current Git Status",
        "```text",
        *current_status_lines,
        "```",
    ]
    base_manifest = existing_manifest.rstrip() if existing_manifest.strip() else (
        "# Repo Change Manifest\n\n"
        + render_header("S08", "Unified Reject Closure", run_id, timestamp)
        + "RepoChangeManifestStatus: synthesized\n"
    ).rstrip()
    created_or_updated.append(write_text(manifest_path, base_manifest + "\n" + "\n".join(manifest_append) + "\n"))

    final_summary = (
        "# Final Summary\n\n"
        + render_header("S08", "Unified Reject Closure", run_id, timestamp)
        + "direct reject\n"
        + f"reason: {reason}\n"
    )
    created_or_updated.append(write_text(run_dir / "final-summary.md", final_summary))
    return created_or_updated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize S01 initialization artifacts and S08 reject closure artifacts for cmux remediation runs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create the S01 initialization artifact set.")
    init_parser.add_argument("--run-dir", required=True)
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--repo-root", default=str(REPO_ROOT))

    reject_parser = subparsers.add_parser("reject", help="Close a run via S08 reject closure.")
    reject_parser.add_argument("--run-dir", required=True)
    reject_parser.add_argument("--run-id", required=True)
    reject_parser.add_argument("--reason", required=True)
    reject_parser.add_argument("--repo-root", default=str(REPO_ROOT))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    if args.command == "init":
        created = initialize_run(run_dir=run_dir, run_id=args.run_id, repo_root=repo_root)
    else:
        created = finalize_reject(
            run_dir=run_dir,
            run_id=args.run_id,
            reason=args.reason,
            repo_root=repo_root,
        )
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
