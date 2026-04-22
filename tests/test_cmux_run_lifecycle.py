#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "workspace/tools/cmux_run_lifecycle.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_run_lifecycle import finalize_reject, initialize_run  # noqa: E402
from workspace.tools.current_task_source import build_main_thread_task_source_ref  # noqa: E402


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)


def test_initialize_run_defaults_do_not_capture_workbot_protected_paths() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        run_dir = repo_root / "workspace/memory/tmp/run-defaults"

        initialize_run(run_dir=run_dir, run_id="run-defaults", repo_root=repo_root)

        baseline_text = (run_dir / "protected-files-baseline.txt").read_text(encoding="utf-8")
        assert "ProtectedFile::" not in baseline_text
        assert "ProtectedDir::" not in baseline_text
        assert str(REPO_ROOT / "AGENTS.md") not in baseline_text
        assert (
            str(REPO_ROOT / "workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md")
            not in baseline_text
        )

        external_text = (run_dir / "external-protected-check.md").read_text(encoding="utf-8")
        assert str(Path("/Users/busiji/.agents/skills/cmux/scripts").resolve()) not in external_text
        assert str(Path("/Users/busiji/.agents/skills/cmux/references").resolve()) not in external_text
        assert str(Path("/Users/busiji/.claude/agents").resolve()) not in external_text


def test_cli_init_smoke_supports_direct_script_execution() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        run_dir = repo_root / "workspace/memory/tmp/run-cli"

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "init",
                "--run-dir",
                str(run_dir),
                "--run-id",
                "run-cli",
                "--repo-root",
                str(repo_root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert str(run_dir / "current-task-source.json") in result.stdout
        baseline_text = (run_dir / "protected-files-baseline.txt").read_text(encoding="utf-8")
        assert "ProtectedFile::" not in baseline_text
        assert str(REPO_ROOT / "AGENTS.md") not in baseline_text


def test_initialize_run_rejects_main_thread_run_dir_under_repo_truth_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        run_dir = repo_root / "workspace/projects/run-invalid"

        try:
            initialize_run(run_dir=run_dir, run_id="run-invalid", repo_root=repo_root)
        except RuntimeError as exc:
            assert "main_thread run_dir must stay under designated run/evidence roots" in str(exc)
            assert str(run_dir) in str(exc)
        else:
            raise AssertionError("expected repo truth run_dir to be rejected")


def test_initialize_run_rejects_provided_main_thread_task_source_ref_outside_run_dir() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        run_dir = repo_root / "workspace/memory/tmp/run-guarded"
        pinned_elsewhere = repo_root / "workspace/memory/tmp/run-other"
        task_source_ref = build_main_thread_task_source_ref(
            request_id="run-guarded",
            deliverable_path=str(pinned_elsewhere),
            evidence_path=str(pinned_elsewhere),
            status="initialized",
            acceptance_owner="main-thread",
        )

        try:
            initialize_run(
                run_dir=run_dir,
                run_id="run-guarded",
                task_source_ref=task_source_ref,
                repo_root=repo_root,
            )
        except RuntimeError as exc:
            assert "main_thread deliverable_path must stay pinned to run_dir" in str(exc)
            assert f"expected={run_dir.resolve()}" in str(exc)
            assert f"actual={pinned_elsewhere.resolve()}" in str(exc)
        else:
            raise AssertionError("expected mismatched main_thread task_source_ref to be rejected")


def test_initialize_run_materializes_full_s01_file_set() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        protected_file = repo_root / "AGENTS.md"
        protected_file.write_text("repo truth\n", encoding="utf-8")
        protected_dir = repo_root / "workspace/memory/tmp/v13"
        protected_dir.mkdir(parents=True)
        (protected_dir / "evidence.txt").write_text("legacy\n", encoding="utf-8")
        external_dir = repo_root / "external"
        external_dir.mkdir()
        (external_dir / "hook.py").write_text("print('ok')\n", encoding="utf-8")
        run_dir = repo_root / "workspace/memory/tmp/run-001"

        created = initialize_run(
            run_dir=run_dir,
            run_id="run-001",
            repo_root=repo_root,
            protected_files=[protected_file],
            protected_dirs=[protected_dir],
            external_paths=[external_dir],
        )

        created_names = {path.name for path in created}
        assert "protected-files-baseline.txt" in created_names
        assert "repo-change-manifest.md" in created_names
        assert "external-protected-check.md" in created_names
        assert "execution-log.md" in created_names
        assert "scope-and-targets.md" in created_names
        assert "unresolved-items.md" in created_names
        assert "permission-mode-trace.md" in created_names
        assert "control-packet-trace.md" in created_names
        assert "a7-finish-trace.md" in created_names
        assert "test-plan.md" in created_names
        assert "current-task-source.json" in created_names
        assert "StepId: S01" in (run_dir / "execution-log.md").read_text(encoding="utf-8")
        task_source = json.loads((run_dir / "current-task-source.json").read_text(encoding="utf-8"))
        assert task_source["task_source_id"] == "main_thread:run-001"
        assert "RepoChangeManifestStatus: baseline-recorded" in (
            run_dir / "repo-change-manifest.md"
        ).read_text(encoding="utf-8")


def test_finalize_reject_writes_final_summary_and_marks_clean_when_protected_unchanged() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        protected_file = repo_root / "AGENTS.md"
        protected_file.write_text("repo truth\n", encoding="utf-8")
        protected_dir = repo_root / "workspace/memory/tmp/v13"
        protected_dir.mkdir(parents=True)
        (protected_dir / "evidence.txt").write_text("legacy\n", encoding="utf-8")
        external_dir = repo_root / "external"
        external_dir.mkdir()
        (external_dir / "hook.py").write_text("print('ok')\n", encoding="utf-8")
        run_dir = repo_root / "workspace/memory/tmp/run-002"

        initialize_run(
            run_dir=run_dir,
            run_id="run-002",
            repo_root=repo_root,
            protected_files=[protected_file],
            protected_dirs=[protected_dir],
            external_paths=[external_dir],
        )
        updated = finalize_reject(
            run_dir=run_dir,
            run_id="run-002",
            reason="abandoned invalid run",
            repo_root=repo_root,
            protected_files=[protected_file],
            protected_dirs=[protected_dir],
            external_paths=[external_dir],
        )

        updated_names = {path.name for path in updated}
        assert "protected-files-diff.txt" in updated_names
        assert "final-summary.md" in updated_names
        assert "direct reject" in (run_dir / "final-summary.md").read_text(encoding="utf-8")
        diff_text = (run_dir / "protected-files-diff.txt").read_text(encoding="utf-8")
        assert "ProtectedDiffStatus: clean" in diff_text
        external_text = (run_dir / "external-protected-check.md").read_text(encoding="utf-8")
        assert "EndResult: PASS" in external_text
        task_source = json.loads((run_dir / "current-task-source.json").read_text(encoding="utf-8"))
        assert task_source["status"] == "archive_only"


def test_finalize_reject_still_closes_when_protected_file_changed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        init_git_repo(repo_root)
        protected_file = repo_root / "AGENTS.md"
        protected_file.write_text("repo truth\n", encoding="utf-8")
        protected_dir = repo_root / "workspace/memory/tmp/v13"
        protected_dir.mkdir(parents=True)
        (protected_dir / "evidence.txt").write_text("legacy\n", encoding="utf-8")
        external_dir = repo_root / "external"
        external_dir.mkdir()
        (external_dir / "hook.py").write_text("print('ok')\n", encoding="utf-8")
        run_dir = repo_root / "workspace/memory/tmp/run-003"

        initialize_run(
            run_dir=run_dir,
            run_id="run-003",
            repo_root=repo_root,
            protected_files=[protected_file],
            protected_dirs=[protected_dir],
            external_paths=[external_dir],
        )
        protected_file.write_text("repo truth changed\n", encoding="utf-8")

        finalize_reject(
            run_dir=run_dir,
            run_id="run-003",
            reason="protected file drifted before closure",
            repo_root=repo_root,
            protected_files=[protected_file],
            protected_dirs=[protected_dir],
            external_paths=[external_dir],
        )

        diff_text = (run_dir / "protected-files-diff.txt").read_text(encoding="utf-8")
        assert "ProtectedDiffStatus: dirty" in diff_text
        final_summary = (run_dir / "final-summary.md").read_text(encoding="utf-8")
        assert "reason: protected file drifted before closure" in final_summary
        task_source = json.loads((run_dir / "current-task-source.json").read_text(encoding="utf-8"))
        assert task_source["status"] == "archive_only"
