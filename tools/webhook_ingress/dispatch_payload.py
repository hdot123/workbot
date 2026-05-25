from __future__ import annotations

import re
import uuid
from typing import Any

from .adapter import utc_now_iso

DEFAULT_REPO = "busiji/workbot"
DEFAULT_TARGET_BRANCH = "branch-2"
DEFAULT_PROJECT_NAME = "Webhook Ingress Canary Project"


class FactoryDispatchPayloadBuilder:
    def __init__(
        self,
        *,
        repo: str = DEFAULT_REPO,
        target_branch: str = DEFAULT_TARGET_BRANCH,
        project_name: str = DEFAULT_PROJECT_NAME,
    ):
        self.repo = repo
        self.target_branch = target_branch
        self.project_name = project_name

    def build(self, canonical_event: dict[str, Any]) -> dict[str, Any]:
        payload = canonical_event.get("payload") or {}
        source = canonical_event.get("source") or {}
        issue_key = str(payload.get("identifier") or source.get("resource_id") or "linear-issue")
        title = str(payload.get("title") or "")
        description = str(payload.get("description") or "")
        branch_name = _suggested_branch_name(issue_key, title)
        return {
            "dispatch_mode": "dry_run",
            "dispatch_type": "factory_main_thread",
            "dispatch_id": f"disp_{uuid.uuid4()}",
            "generated_at": utc_now_iso(),
            # P1 safety flags — all dry-run, no real execution
            "dry_run": True,
            "no_write": True,
            "no_push": True,
            "no_deploy": True,
            "github_push_forbidden": True,
            "required_ci": "gitlab",
            "parent_droid_role": "coordinator_acceptance_only",
            "stop_condition": {
                "no_real_factory_dispatch_in_p1": True,
                "implementer_allowed_only_in_dry_run_plan": True,
                "reviewer_auditor_required_before_real_execution": True,
            },
            "linear_issue_id": source.get("resource_id") or payload.get("id"),
            "linear_issue_key": issue_key,
            "title": title,
            "description": description,
            "acceptance_criteria": _extract_acceptance_criteria(description),
            "project_id": source.get("project_id") or payload.get("project_id"),
            "project_name": payload.get("project_name") or self.project_name,
            "repo": self.repo,
            "target_branch": self.target_branch,
            "suggested_branch_name": branch_name,
            "ci_required": True,
            "gitlab_required": True,
            "max_bailian_agents": 10,
            "min_bailian_agents": 1,
            "required_review_agents": 1,
            "max_fix_attempts": 3,
            "main_thread_policy": {
                "must_not_implement_code": True,
                "responsibilities": ["understand_goal", "decompose_tasks", "dispatch_subagents", "supervise", "summarize", "final_acceptance"],
                "must_summarize_after_subagents": True,
            },
            "subagent_policy": {
                "implementation_by_bailian_only": True,
                "min_bailian_agents": 1,
                "max_bailian_agents": 10,
                "required_review_agents": 1,
                "recommended_split": ["development", "tests", "security", "documentation", "acceptance_audit"],
            },
            "acceptance_policy": {
                "linear_acceptance_criteria_required": True,
                "gitlab_ci_must_pass": True,
                "review_subagent_must_report": "PASS_or_FAIL",
            },
            "ci_policy": {
                "gitlab_ci_is_machine_gate": True,
                "do_not_mark_done_when_ci_fails": True,
                "generate_fix_dispatch_on_ci_failure": True,
            },
            "loop_guard_policy": {
                "max_auto_fix_attempts_per_issue": 3,
                "same_failure_hash_not_redispatched": True,
                "duplicate_webhook_not_redispatched": True,
                "comment_created_does_not_dispatch": True,
            },
            "source_event": {
                "canonical_event_id": canonical_event.get("event_id"),
                "idempotency_key": canonical_event.get("idempotency_key"),
                "raw_body_sha256": canonical_event.get("raw_body_sha256"),
            },
        }


def _suggested_branch_name(issue_key: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "factory-task"
    return f"factory/{issue_key.lower()}-{slug}"


def _extract_acceptance_criteria(description: str) -> list[str]:
    lines = [line.strip(" -\t") for line in description.splitlines()]
    criteria = [line for line in lines if line and any(marker in line.lower() for marker in ("accept", "验收", "pass", "must", "必须"))]
    return criteria or ["Satisfy the Linear issue acceptance criteria", "GitLab CI must pass", "Acceptance/audit subagent must report PASS"]
