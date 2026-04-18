from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


CMUX_SCRIPT_DIR = Path.home() / ".agents" / "skills" / "cmux" / "scripts"
GENERATE_ASSIGNMENTS_PATH = CMUX_SCRIPT_DIR / "generate_cmux_assignments.py"


def load_generate_assignments_module():
    if not GENERATE_ASSIGNMENTS_PATH.exists():
        pytest.skip(f"global generate_cmux_assignments missing: {GENERATE_ASSIGNMENTS_PATH}")
    if str(CMUX_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(CMUX_SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("generate_cmux_assignments", GENERATE_ASSIGNMENTS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec for {GENERATE_ASSIGNMENTS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_valid_active_assignment(module, *, bot_name: str = "dev-bot") -> dict[str, object]:
    item = module.base_assignment(bot_name, workspace_root="/Users/busiji/workbot", project_scope="workbot")
    item.update(
        {
            "status": "ACTIVE",
            "assignment_id": f"{bot_name}-001",
            "workspace_ref": "workspace:1",
            "pane_ref": "pane:1",
            "surface_ref": "surface:1",
            "title": "P10-rest dispatch contract check",
            "goal": "validate bootstrap and dispatch contract convergence",
            "assignment_class": "已批准执行方案",
            "lane_justification": "implement approved task using the runtime contract",
            "target_object": "runtime dispatch contract",
            "scope_boundary": "phase-3 p10-rest",
            "deliverable": "validated dispatch gate",
            "verification_goal": "gate must reject drift before launch",
            "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
            "tool_profile_id": "dev-active",
            "allowed_tools": ["Read", "Bash"],
            "forbidden_tools": [],
            "allowed_write_target": "/Users/busiji/workbot",
            "permission_mode": "default",
            "dispatch_owner": "codex",
            "conflict_status": "clean",
            "lane_identity": bot_name,
            "worker_role": module.lane_from_bot_name(bot_name),
        }
    )
    return item


def test_dispatch_blockers_accept_valid_active_assignment() -> None:
    module = load_generate_assignments_module()
    item = make_valid_active_assignment(module, bot_name="dev-bot")
    blockers = module.dispatch_blockers(item)
    assert blockers == []


def test_dispatch_blockers_flag_dispatch_owner_drift() -> None:
    module = load_generate_assignments_module()
    item = make_valid_active_assignment(module, bot_name="dev-bot")
    item["dispatch_owner"] = "pm-bot"
    blockers = module.dispatch_blockers(item)
    assert "dispatch_owner.not_codex" in blockers


def test_dispatch_blockers_flag_lane_identity_drift() -> None:
    module = load_generate_assignments_module()
    item = make_valid_active_assignment(module, bot_name="qa-bot")
    item["lane_identity"] = "doc-bot"
    blockers = module.dispatch_blockers(item)
    assert "lane_identity.bot_name_mismatch" in blockers


def test_dispatch_blockers_flag_worker_role_drift() -> None:
    module = load_generate_assignments_module()
    item = make_valid_active_assignment(module, bot_name="rea-bot")
    item["worker_role"] = "qa"
    blockers = module.dispatch_blockers(item)
    assert "worker_role.bot_name_mismatch" in blockers
