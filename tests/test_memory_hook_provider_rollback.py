#!/usr/bin/env python3
"""Rollback drill quality gates for memory_hook_provider_rollback."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools import memory_hook_provider_rollback as rollback


def test_rollback_drill_fails_when_external_probe_raises(monkeypatch):
    def fake_resolve(provider: str):
        if provider == "external-core":
            raise RuntimeError("external unavailable")
        return "legacy", object(), []

    monkeypatch.setattr(rollback.gateway, "_resolve_core_builder", fake_resolve)
    result = rollback.run_rollback_drill()
    assert result["external_probe_ok"] is False
    assert result["status"] == "failed"


def test_rollback_drill_passes_when_external_probe_is_external_and_legacy_is_clean(monkeypatch):
    def fake_resolve(provider: str):
        if provider == "external-core":
            return "external-core", object(), []
        return "legacy", object(), []

    monkeypatch.setattr(rollback.gateway, "_resolve_core_builder", fake_resolve)
    result = rollback.run_rollback_drill()
    assert result["external_probe_ok"] is True
    assert result["legacy_probe_ok"] is True
    assert result["status"] == "passed"


def test_rollback_drill_fails_when_legacy_probe_raises(monkeypatch):
    def fake_resolve(provider: str):
        if provider == "external-core":
            return "external-core", object(), []
        raise RuntimeError("legacy unavailable")

    monkeypatch.setattr(rollback.gateway, "_resolve_core_builder", fake_resolve)
    result = rollback.run_rollback_drill()
    assert result["external_probe_ok"] is True
    assert result["legacy_probe_ok"] is False
    assert result["status"] == "failed"
