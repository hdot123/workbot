#!/usr/bin/env python3
"""Policy conflict resolution tests for memory_hook_impls."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.memory_hook_impls import PolicyRegistryImpl


def test_prefer_strict_registration_phase_prefers_enforced():
    registry = PolicyRegistryImpl()
    resolved = registry.resolve_conflict(
        "registration_phase",
        ["declared-not-enforced", "enforced"],
        "prefer-strict",
    )
    assert resolved == "enforced"


def test_prefer_strict_registration_phase_keeps_existing_value_when_no_enforced():
    registry = PolicyRegistryImpl()
    resolved = registry.resolve_conflict(
        "registration_phase",
        ["declared-not-enforced"],
        "prefer-strict",
    )
    assert resolved == "declared-not-enforced"
