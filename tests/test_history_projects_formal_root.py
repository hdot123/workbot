#!/usr/bin/env python3
"""Coverage for the formal history-projects root contract."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.memory_hook_gateway import (
    HISTORY_PROJECTS_INDEX_PATH,
    HISTORY_PROJECTS_ROOT,
    LOWER_EVIDENCE_ROOTS,
    REQUIRED_GATEWAY_INPUTS,
    REQUIRED_REGISTRY_SCOPES,
    classify_truth_ref,
    lower_evidence_ref,
    validate_unique_legal_system_contract,
)


def test_history_projects_index_is_required_gateway_input():
    assert HISTORY_PROJECTS_INDEX_PATH == HISTORY_PROJECTS_ROOT / "INDEX.md"
    assert HISTORY_PROJECTS_INDEX_PATH in REQUIRED_GATEWAY_INPUTS


def test_history_projects_root_is_registered_and_classified_as_history():
    assert "history-projects/**" in REQUIRED_REGISTRY_SCOPES
    assert HISTORY_PROJECTS_ROOT in LOWER_EVIDENCE_ROOTS
    assert classify_truth_ref(HISTORY_PROJECTS_INDEX_PATH) == "history-root"
    assert lower_evidence_ref(HISTORY_PROJECTS_INDEX_PATH) is True


def test_unique_legal_system_contract_accepts_history_projects_root():
    assert validate_unique_legal_system_contract() == []
