#!/usr/bin/env python3
"""M9 provider tests: external-core fail-closed and explicit rollback."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools import memory_hook_gateway as gateway


class FakeBusinessPolicy:
    def determine_project_scope(self, cwd):
        return "workbot"

    def project_map_refs(self):
        return []

    def get_required_gateway_inputs(self):
        return []

    def get_project_canonical(self):
        return {"workbot": gateway.WORKSPACE_ROOT / "memory" / "kb" / "projects" / "workbot.md"}

    def get_project_runtime_root(self):
        return {"workbot": gateway.WORKSPACE_ROOT / "projects"}

    def get_global_canonical(self):
        return []

    def validate_project_map_files(self):
        return []

    def validate_unique_legal_system_contract(self):
        return []


def test_resolve_core_builder_defaults_to_legacy():
    provider, builder, errors = gateway._resolve_core_builder("legacy")
    assert provider == "legacy"
    assert callable(builder)
    assert errors == []


def test_resolve_core_builder_raises_when_external_load_fails(monkeypatch):
    monkeypatch.setattr(
        gateway,
        "_load_external_core_builder",
        lambda: (_ for _ in ()).throw(RuntimeError("external unavailable")),
    )
    with pytest.raises(RuntimeError, match="external unavailable"):
        gateway._resolve_core_builder("external-core")


def test_resolve_core_builder_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported MEMORY_HOOK_CORE_PROVIDER"):
        gateway._resolve_core_builder("unknown-provider")


def test_load_external_core_builder_from_external_path(tmp_path: Path, monkeypatch):
    workspace_pkg = tmp_path / "workspace"
    tools_pkg = workspace_pkg / "tools"
    tools_pkg.mkdir(parents=True)
    (workspace_pkg / "__init__.py").write_text("", encoding="utf-8")
    (tools_pkg / "__init__.py").write_text("", encoding="utf-8")
    (tools_pkg / "memory_hook_core.py").write_text(
        "def build_context_package_core(*args, **kwargs):\n"
        "    return {'from': 'external-core-path'}\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("MEMORY_HOOK_EXTERNAL_CORE_PATH", str(tmp_path))
    monkeypatch.setenv("MEMORY_HOOK_EXTERNAL_CORE_MODULE", "workspace.tools.memory_hook_core")
    monkeypatch.setenv("MEMORY_HOOK_EXTERNAL_CORE_FUNC", "build_context_package_core")

    builder = gateway._load_external_core_builder()
    assert builder()["from"] == "external-core-path"


def test_load_external_core_builder_raises_when_configured_module_missing(monkeypatch):
    monkeypatch.setenv("MEMORY_HOOK_EXTERNAL_CORE_MODULE", "does.not.exist.module")
    monkeypatch.delenv("MEMORY_HOOK_EXTERNAL_CORE_PATH", raising=False)
    with pytest.raises(ImportError, match="does.not.exist.module"):
        gateway._load_external_core_builder()


def test_build_context_package_external_load_failure_requires_manual_rollback(monkeypatch):
    monkeypatch.setattr(gateway, "_get_gateway_business_policy", lambda: FakeBusinessPolicy())
    monkeypatch.setattr(gateway, "discover_cwd", lambda payload: gateway.WORKSPACE_ROOT)
    monkeypatch.setattr(gateway, "determine_project_scope", lambda cwd: "workbot")
    monkeypatch.setenv("MEMORY_HOOK_CORE_PROVIDER", "external-core")

    def fake_resolve(provider: str):
        if provider == "external-core":
            raise RuntimeError("external unavailable")
        raise AssertionError("unexpected provider")

    monkeypatch.setattr(gateway, "_resolve_core_builder", fake_resolve)

    package = gateway.build_context_package("codex", "session-start", {})

    assert package["status"] == "degraded"
    assert package["system_context"]["core_provider"] == "external-core"
    assert package["system_context"]["core_provider_requested"] == "external-core"
    assert package["system_context"]["core_provider_release_ref"] == gateway.EXTERNAL_CORE_RELEASE_REF
    assert package["system_context"]["core_provider_manual_rollback_required"] is True
    assert any("manual rollback required" in item for item in package["system_context"]["warnings"])
    assert any("manual rollback required" in item for item in package["system_context"]["core_provider_errors"])
    assert any("manual rollback required" in item for item in package["validation_errors"])


def test_build_context_package_defaults_to_external_core_provider(monkeypatch):
    monkeypatch.setattr(gateway, "_get_gateway_business_policy", lambda: FakeBusinessPolicy())
    monkeypatch.setattr(gateway, "discover_cwd", lambda payload: gateway.WORKSPACE_ROOT)
    monkeypatch.setattr(gateway, "determine_project_scope", lambda cwd: "workbot")
    monkeypatch.delenv("MEMORY_HOOK_CORE_PROVIDER", raising=False)

    captured: dict[str, str] = {}

    def external_builder(**kwargs):
        return {"status": "ok", "validation_errors": [], "system_context": {}}

    def fake_resolve(provider: str):
        captured["provider"] = provider
        return "external-core", external_builder, []

    monkeypatch.setattr(gateway, "_resolve_core_builder", fake_resolve)

    package = gateway.build_context_package("codex", "session-start", {})

    assert captured["provider"] == "external-core"
    assert package["status"] == "ok"
    assert package["system_context"]["core_provider"] == "external-core"
    assert package["system_context"]["core_provider_requested"] == "external-core"
    assert package["system_context"]["core_provider_release_ref"] == gateway.EXTERNAL_CORE_RELEASE_REF


def test_main_returns_nonzero_when_external_load_fails_without_explicit_rollback(monkeypatch):
    monkeypatch.setattr(gateway, "_get_gateway_business_policy", lambda: FakeBusinessPolicy())
    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="codex", event="session-start", no_delegate=True),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "write_artifacts", lambda package: {"snapshot": "s", "latest": "l"})
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO("{}"))
    monkeypatch.setenv("MEMORY_HOOK_CORE_PROVIDER", "external-core")

    def fake_resolve(provider: str):
        if provider == "external-core":
            raise RuntimeError("external unavailable")
        raise AssertionError("unexpected provider")

    monkeypatch.setattr(gateway, "_resolve_core_builder", fake_resolve)

    rc = gateway.main()
    assert rc == 1


def test_main_returns_zero_when_explicit_legacy_provider(monkeypatch):
    monkeypatch.setattr(gateway, "_get_gateway_business_policy", lambda: FakeBusinessPolicy())
    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="codex", event="session-start", no_delegate=True),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "write_artifacts", lambda package: {"snapshot": "s", "latest": "l"})
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO("{}"))
    monkeypatch.setenv("MEMORY_HOOK_CORE_PROVIDER", "legacy")

    def legacy_builder(**kwargs):
        return {"status": "ok", "validation_errors": [], "system_context": {}}

    monkeypatch.setattr(gateway, "_resolve_core_builder", lambda provider: ("legacy", legacy_builder, []))

    rc = gateway.main()
    assert rc == 0
