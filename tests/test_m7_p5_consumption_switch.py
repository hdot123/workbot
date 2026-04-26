#!/usr/bin/env python3
"""M7-P5: Verify workbot consumes memory repo published core, not local copy."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "workspace" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _fresh_gateway():
    """Force reload gateway to pick up env changes."""
    for mod in list(sys.modules):
        if "memory_hook" in mod:
            del sys.modules[mod]
    import memory_hook_gateway
    importlib = pytest.importorskip("importlib")
    importlib.reload(memory_hook_gateway)
    return memory_hook_gateway


class TestExternalCoreFromMemoryRepo:
    """Verify external-core provider loads from the memory repo."""

    def test_external_core_module_is_not_local(self):
        gw = _fresh_gateway()
        result = gw.build_context_package("workbot", "test", {})
        sc = result.get("system_context", {})
        module = sc.get("core_provider_module", "")
        # _external_ prefix means it was loaded via spec_from_file_location
        assert module.startswith("_external_"), (
            f"core should load from external path, got module: {module}"
        )

    def test_external_core_release_ref_points_to_memory_repo(self):
        gw = _fresh_gateway()
        result = gw.build_context_package("workbot", "test", {})
        sc = result.get("system_context", {})
        ref = sc.get("core_provider_release_ref", "")
        assert "hdot123/memory" in ref, f"release ref should point to memory repo: {ref}"

    def test_external_core_provider_name(self):
        gw = _fresh_gateway()
        result = gw.build_context_package("workbot", "test", {})
        sc = result.get("system_context", {})
        assert sc.get("core_provider") == "external-core"

    def test_gateway_uses_required_canonical_kwarg(self):
        """Verify gateway passes required_canonical (not required_gateway_inputs)."""
        import inspect
        gw = _fresh_gateway()
        source = inspect.getsource(gw.build_context_package)
        assert "required_canonical=" in source, (
            "gateway should pass required_canonical= to core builder"
        )
        assert "required_gateway_inputs=" not in source, (
            "gateway should not use old required_gateway_inputs= kwarg"
        )


class TestLegacyFallbackStillWorks:
    """Verify legacy provider still works as rollback target."""

    def test_legacy_provider_returns_package(self):
        os.environ["MEMORY_HOOK_CORE_PROVIDER"] = "legacy"
        try:
            gw = _fresh_gateway()
            result = gw.build_context_package("workbot", "test", {})
            assert result.get("status") in ("ok", "degraded")
            sc = result.get("system_context", {})
            assert sc.get("core_provider") == "legacy"
        finally:
            os.environ.pop("MEMORY_HOOK_CORE_PROVIDER", None)


class TestRollbackDrill:
    """Verify rollback drill passes with both providers."""

    def test_rollback_drill_passes(self):
        from memory_hook_provider_rollback import run_rollback_drill
        result = run_rollback_drill()
        assert result["status"] == "passed", f"rollback drill failed: {result}"
        assert result["external_probe_ok"] is True
        assert result["legacy_probe_ok"] is True
