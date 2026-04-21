#!/usr/bin/env python3
"""ISSUE-007: Tests for WORKBOT_FORCE_HOOK external cwd scope misclassification fix."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repository root to Python path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.memory_hook_gateway import (
    REPO_ROOT,
    build_context_package,
    determine_project_scope,
    discover_cwd,
    path_within_repo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_env(key):
    return os.environ.get(key)

def _restore_env(key, old):
    if old is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = old

# ---------------------------------------------------------------------------
# Tests: path_within_repo
# ---------------------------------------------------------------------------

def test_path_within_repo_repo_root():
    assert path_within_repo(REPO_ROOT) is True

def test_path_within_repo_workspace():
    assert path_within_repo(REPO_ROOT / "workspace") is True

def test_path_within_repo_external():
    assert path_within_repo(Path("/tmp/notrepo/workbot/app/fake")) is False

def test_path_within_repo_tmp():
    assert path_within_repo(Path("/tmp/something")) is False

# ---------------------------------------------------------------------------
# Tests: discover_cwd
# ---------------------------------------------------------------------------

def test_discover_cwd_no_payload_no_env():
    old_pwd = _save_env("PWD")
    os.environ.pop("PWD", None)
    try:
        result = discover_cwd({})
        assert result == REPO_ROOT, f"expected {REPO_ROOT}, got {result}"
    finally:
        _restore_env("PWD", old_pwd)

def test_discover_cwd_external_env_cwd():
    """When PWD is an external path, discover_cwd returns it (existing behavior preserved)."""
    old_pwd = _save_env("PWD")
    os.environ["PWD"] = "/tmp/notrepo/workbot/app/fake"
    try:
        result = discover_cwd({})
        assert result == Path("/tmp/notrepo/workbot/app/fake"), f"expected external cwd, got {result}"
    finally:
        _restore_env("PWD", old_pwd)

# ---------------------------------------------------------------------------
# Tests: determine_project_scope  (ISSUE-007 core)
# ---------------------------------------------------------------------------

def test_scope_external_cwd_fallback_to_workbot():
    """External non-repo cwd must NOT drive project_scope to platform-capabilities."""
    external = Path("/tmp/notrepo/workbot/app/fake")
    assert determine_project_scope(external) == "workbot"

def test_scope_external_cwd_aedu_like_fallback():
    """External path mimicking AEdu pattern also falls back safely."""
    external = Path("/tmp/notrepo/workbot/AEdu/src")
    assert determine_project_scope(external) == "workbot"

def test_scope_external_cwd_gpt_like_fallback():
    """External path mimicking gpt-web-to pattern falls back safely."""
    external = Path("/tmp/workbot/gpt-web-to/lib")
    assert determine_project_scope(external) == "workbot"

def test_scope_internal_aedu():
    """Internal AEdu cwd should still classify as AEdu."""
    assert determine_project_scope(REPO_ROOT / "AEdu") == "AEdu"
    assert determine_project_scope(REPO_ROOT / "workspace" / "projects" / "AEdu") == "AEdu"

def test_scope_internal_app_platform():
    """Internal app cwd should still classify as platform-capabilities."""
    assert determine_project_scope(REPO_ROOT / "app") == "platform-capabilities"
    assert determine_project_scope(REPO_ROOT / "app" / "src") == "platform-capabilities"

def test_scope_internal_agents_platform():
    """Internal agents cwd should still classify as platform-capabilities."""
    assert determine_project_scope(REPO_ROOT / "agents") == "platform-capabilities"

def test_scope_internal_gpt_web_to_platform():
    """Internal gpt-web-to cwd should still classify as platform-capabilities."""
    assert determine_project_scope(REPO_ROOT / "gpt-web-to") == "platform-capabilities"

def test_scope_internal_workspace_root_defaults_workbot():
    """Repo-internal workspace root defaults to workbot."""
    assert determine_project_scope(REPO_ROOT / "workspace") == "workbot"

def test_scope_repo_root_defaults_workbot():
    assert determine_project_scope(REPO_ROOT) == "workbot"

# ---------------------------------------------------------------------------
# Tests: build_context_package with forced external cwd (ISSUE-007 integration)
# ---------------------------------------------------------------------------

def test_build_context_package_forced_external_cwd():
    """With WORKBOT_FORCE_HOOK=1 and external PWD, project_scope must still be workbot."""
    old_force = _save_env("WORKBOT_FORCE_HOOK")
    old_pwd = _save_env("PWD")
    os.environ["WORKBOT_FORCE_HOOK"] = "1"
    os.environ["PWD"] = "/tmp/notrepo/workbot/app/fake"
    try:
        pkg = build_context_package("codex", "session-start", {})
        assert pkg["project_scope"] == "workbot", (
            f"forced external cwd leaked into project_scope: {pkg['project_scope']}"
        )
    finally:
        _restore_env("WORKBOT_FORCE_HOOK", old_force)
        _restore_env("PWD", old_pwd)

def test_build_context_package_safe_internal_cwd():
    """Internal cwd should not be affected by the fix."""
    old_force = _save_env("WORKBOT_FORCE_HOOK")
    old_pwd = _save_env("PWD")
    os.environ.pop("WORKBOT_FORCE_HOOK", None)
    os.environ["PWD"] = str(REPO_ROOT / "AEdu")
    try:
        pkg = build_context_package("codex", "session-start", {})
        assert pkg["project_scope"] == "AEdu", (
            f"internal AEdu cwd misclassified: {pkg['project_scope']}"
        )
    finally:
        _restore_env("WORKBOT_FORCE_HOOK", old_force)
        _restore_env("PWD", old_pwd)


def test_build_context_package_marks_codex_without_cmux_binding_as_external_session():
    old_workspace = _save_env("CMUX_WORKSPACE_ID")
    old_surface = _save_env("CMUX_SURFACE_ID")
    old_provider = _save_env("MEMORY_HOOK_CORE_PROVIDER")
    os.environ.pop("CMUX_WORKSPACE_ID", None)
    os.environ.pop("CMUX_SURFACE_ID", None)
    os.environ["MEMORY_HOOK_CORE_PROVIDER"] = "legacy"
    try:
        pkg = build_context_package("codex", "prompt-submit", {"session_id": "sess-external"})
        task_context = pkg["task_context"]
        assert task_context["session_class"] == "external_session"
        assert task_context["formal_worker_session"] is False
        assert task_context["binding_complete"] is False
        assert task_context["binding_basis"] == "external_main_thread"
    finally:
        _restore_env("CMUX_WORKSPACE_ID", old_workspace)
        _restore_env("CMUX_SURFACE_ID", old_surface)
        _restore_env("MEMORY_HOOK_CORE_PROVIDER", old_provider)


def test_build_context_package_marks_complete_cmux_binding_as_formal_worker():
    old_workspace = _save_env("CMUX_WORKSPACE_ID")
    old_surface = _save_env("CMUX_SURFACE_ID")
    old_provider = _save_env("MEMORY_HOOK_CORE_PROVIDER")
    os.environ["CMUX_WORKSPACE_ID"] = "workspace:9"
    os.environ["CMUX_SURFACE_ID"] = "surface:9"
    os.environ["MEMORY_HOOK_CORE_PROVIDER"] = "legacy"
    try:
        pkg = build_context_package("claude", "session-start", {"session_id": "sess-worker"})
        task_context = pkg["task_context"]
        assert task_context["session_class"] == "formal_cmux_worker"
        assert task_context["formal_worker_session"] is True
        assert task_context["binding_complete"] is True
        assert task_context["binding_basis"] == "cmux_workspace_surface"
        assert task_context["binding_errors"] == []
    finally:
        _restore_env("CMUX_WORKSPACE_ID", old_workspace)
        _restore_env("CMUX_SURFACE_ID", old_surface)
        _restore_env("MEMORY_HOOK_CORE_PROVIDER", old_provider)

# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
