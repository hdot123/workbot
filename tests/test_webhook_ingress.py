#!/usr/bin/env python3
# CI gate: validated via GitLab CI webhook-ingress-pytest (P0-2G v2)
from __future__ import annotations

import hmac
import hashlib
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.webhook_ingress.actions import ActionRegistry, FactoryDispatchDryRunAction, LinearCanaryCommentAction
from workspace.tools.webhook_ingress.adapter import LinearAdapter, SignatureInvalidError
from workspace.tools.webhook_ingress.dispatch_payload import FactoryDispatchPayloadBuilder
from workspace.tools.webhook_ingress.executors import FactoryDispatchDryRunExecutor, LinearCanaryCommentResult
from workspace.tools.webhook_ingress.ingress import WebhookIngress
from workspace.tools.webhook_ingress.models import WebhookRequest
from workspace.tools.webhook_ingress.routes import RouteMatcher
from workspace.tools.webhook_ingress.schema import validate_canonical_event
from workspace.tools.webhook_ingress.storage import WebhookEventStore

SECRET = "test-linear-secret"


class FakeCanaryExecutor:
    def __init__(self, comments: list[str], *, fail: bool = False):
        self.comments = comments
        self.fail = fail

    def execute(self, canonical_event: dict) -> LinearCanaryCommentResult:
        if self.fail:
            raise RuntimeError("boom")
        self.comments.append(canonical_event["event_id"])
        return LinearCanaryCommentResult(comment_id="comment-1")


def canary_registry(comments: list[str], *, fail: bool = False, allowed_project_ids: set[str] | None = None) -> ActionRegistry:
    return ActionRegistry([
        LinearCanaryCommentAction(executor=FakeCanaryExecutor(comments, fail=fail), enabled=True, allowed_project_ids=allowed_project_ids)
    ])


def factory_dispatch_registry(allowed_project_ids: set[str] | None = None) -> ActionRegistry:
    return ActionRegistry([
        FactoryDispatchDryRunAction(
            executor=FactoryDispatchDryRunExecutor(payload_builder=FactoryDispatchPayloadBuilder(repo="busiji/workbot", target_branch="branch-2")),
            enabled=True,
            allowed_project_ids=allowed_project_ids,
        )
    ])


def linear_issue_payload(action: str = "update") -> dict:
    return {
        "type": "Issue",
        "action": action,
        "organizationId": "org-1",
        "data": {
            "id": "issue-1",
            "identifier": "JTO-177",
            "title": "Webhook ingress test",
            "description": "test",
            "url": "https://linear.app/jtoom/issue/JTO-177/test",
            "createdAt": "2026-05-04T00:00:00.000Z",
            "updatedAt": "2026-05-04T00:01:00.000Z",
            "team": {"id": "team-1"},
            "state": {"name": "Backlog"},
            "user": {"id": "user-1", "name": "Ahern li", "email": "x@example.com"},
        },
    }


def body_and_signature(payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, sig


def signed_request(payload: dict | None = None, delivery_id: str = "delivery-1") -> WebhookRequest:
    body, sig = body_and_signature(payload or linear_issue_payload())
    return WebhookRequest(
        provider="linear",
        raw_body=body,
        headers={"Linear-Signature": sig, "Linear-Delivery": delivery_id},
        path="/webhooks/linear",
        source_ip="127.0.0.1",
    )


def test_linear_signature_success():
    adapter = LinearAdapter(SECRET)
    adapter.verify(signed_request())


def test_linear_signature_failure():
    adapter = LinearAdapter(SECRET)
    req = signed_request()
    bad = WebhookRequest(provider=req.provider, raw_body=req.raw_body, headers={"Linear-Signature": "0" * 64}, path=req.path)
    try:
        adapter.verify(bad)
    except SignatureInvalidError as exc:
        assert exc.code == "SIGNATURE_INVALID"
    else:
        raise AssertionError("bad signature should fail")


def test_linear_issue_updated_to_canonical_event_schema():
    adapter = LinearAdapter(SECRET)
    event = adapter.normalize(signed_request(), event_id="evt_00000000-0000-0000-0000-000000000001", received_at="2026-05-04T00:02:00Z")
    validate_canonical_event(event)
    assert event["provider"] == "linear"
    assert event["provider_event_type"] == "Issue"
    assert event["provider_action"] == "update"
    assert event["canonical_type"] == "issue"
    assert event["canonical_action"] == "updated"
    assert event["payload"]["identifier"] == "JTO-177"
    assert event["raw_body_sha256"].startswith("sha256:")


def test_linear_issue_labels_to_canonical_payload():
    payload = linear_issue_payload()
    payload["data"]["labels"] = [{"id": "label-1", "name": "webhook-ingress-canary", "color": "#f59e0b"}]
    payload["data"]["labelIds"] = ["label-1"]
    adapter = LinearAdapter(SECRET)
    event = adapter.normalize(signed_request(payload=payload), event_id="evt_labels", received_at="2026-05-04T00:02:00Z")

    assert event["payload"]["labels"] == ["webhook-ingress-canary"]
    assert event["payload"]["label_ids"] == ["label-1"]


def test_linear_issue_state_transition_to_canonical_payload():
    payload = linear_issue_payload()
    payload["updatedFrom"] = {"stateId": "state-prev", "state": {"id": "state-prev", "name": "Backlog"}}
    payload["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    adapter = LinearAdapter(SECRET)
    event = adapter.normalize(signed_request(payload=payload), event_id="evt_state", received_at="2026-05-04T00:02:00Z")

    assert event["payload"]["state"] == "Ready for Factory"
    assert event["payload"]["state_id"] == "state-ready"
    assert event["payload"]["previous_state"] == "Backlog"
    assert event["payload"]["previous_state_id"] == "state-prev"


def test_linear_issue_project_to_canonical_payload():
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["data"]["project"] = {"id": "project-1", "name": "Webhook Ingress Canary Project", "url": "https://linear.app/project/project-1"}
    adapter = LinearAdapter(SECRET)
    event = adapter.normalize(signed_request(payload=payload), event_id="evt_project", received_at="2026-05-04T00:02:00Z")

    assert event["source"]["project_id"] == "project-1"
    assert event["payload"]["project_id"] == "project-1"
    assert event["payload"]["project_name"] == "Webhook Ingress Canary Project"


def test_ack_response_format_fixed_and_raw_event_stored():
    forwarded = []
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store, n8n_sender=forwarded.append)
    result = ingress.handle(signed_request())

    assert result.http_status == 200
    assert result.ack.to_dict()["ok"] is True
    assert result.ack.to_dict()["status"] == "accepted"
    assert result.ack.to_dict()["provider"] == "linear"
    assert result.ack.to_dict()["request_id"].startswith("req_")
    assert result.ack.to_dict()["event_id"].startswith("evt_")
    assert store.count("webhook_raw_events") == 1
    assert store.count("webhook_canonical_events") == 1
    assert len(forwarded) == 1
    assert forwarded[0]["canonical_version"] == "v1"
    assert forwarded[0]["provider"] == "linear"
    assert "headers" not in forwarded[0]


def test_production_canary_logs_required_forward_details():
    forwarded = []
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store, n8n_sender=forwarded.append, route_mode="production_canary")
    result = ingress.handle(signed_request(delivery_id="prod-canary-log"))

    assert result.http_status == 200
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_forward' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    details = json.loads(row[0])
    assert details["route_name"] == "linear.production_canary"
    assert details["target_type"] == "n8n_canary"
    assert details["status"] == "success"
    assert details["attempt"] == 1
    assert details["canonical_event_id"] == result.ack.to_dict()["event_id"]
    assert details["action_name"] == "forward_to_n8n"
    assert details["idempotency_key"] == "linear:prod-canary-log"


def test_canary_dryrun_forwards_with_delivery_mode_marker():
    forwarded = []
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store, n8n_sender=forwarded.append, route_mode="canary_dryrun")
    result = ingress.handle(signed_request(delivery_id="canary-delivery"))

    assert result.http_status == 200
    assert result.forwarded_to_n8n is True
    assert forwarded[0]["delivery_mode"] == "canary_dryrun"
    assert store.count("webhook_raw_events") == 1
    assert store.count("webhook_canonical_events") == 1


def test_production_canary_comment_only_for_project_issue_update():
    comments = []
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["data"]["project"] = {"id": "project-1", "name": "Webhook Ingress Canary Project"}
    payload["data"]["labels"] = [{"id": "label-similar", "name": "webhook-ingress-canary"}]
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry(comments, allowed_project_ids={"project-1"}),
    )

    result = ingress.handle(signed_request(payload=payload, delivery_id="project-canary-comment-1"))

    assert result.http_status == 200
    assert comments == [result.ack.to_dict()["event_id"]]
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'linear canary comment created' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    details = json.loads(row[0])
    assert details["target_type"] == "linear_comment_canary"
    assert details["status"] == "success"
    assert details["canonical_event_id"] == result.ack.to_dict()["event_id"]
    assert details["action_name"] == "linear_canary_comment"
    assert details["idempotency_key"] == "linear:project-canary-comment-1"
    assert details["project_id"] == "project-1"


def test_production_canary_comment_skips_out_of_project_issue_even_with_similar_label():
    comments = []
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-outside"
    payload["data"]["labels"] = [{"id": "label-similar", "name": "webhook-ingress-canary"}]
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry(comments, allowed_project_ids={"project-1"}),
    )

    result = ingress.handle(signed_request(payload=payload, delivery_id="project-outside-comment-1"))

    assert result.http_status == 200
    assert comments == []
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    details = json.loads(row[0])
    assert details["status"] == "skipped"
    assert details["reason"] == "not_project_scoped_issue_update"
    assert details["project_id"] == "project-outside"


def test_production_canary_comment_only_for_labelled_issue_update():
    comments = []
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["labels"] = [{"id": "label-1", "name": "webhook-ingress-canary"}]
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry(comments),
    )

    result = ingress.handle(signed_request(payload=payload, delivery_id="canary-comment-1"))

    assert result.http_status == 200
    assert comments == [result.ack.to_dict()["event_id"]]
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'linear canary comment created' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    details = json.loads(row[0])
    assert details["target_type"] == "linear_comment_canary"
    assert details["status"] == "success"
    assert details["canonical_event_id"] == result.ack.to_dict()["event_id"]
    assert details["action_name"] == "linear_canary_comment"
    assert details["idempotency_key"] == "linear:canary-comment-1"


def test_production_canary_comment_skips_unmarked_issue_and_comment_events():
    comments = []
    store = WebhookEventStore()
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry(comments),
    )

    issue_result = ingress.handle(signed_request(delivery_id="unmarked-issue"))
    comment_payload = {
        "type": "Comment",
        "action": "create",
        "organizationId": "org-1",
        "data": {
            "id": "comment-1",
            "body": "[webhook-ingress-canary] loop candidate",
            "url": "https://linear.app/jtoom/issue/JTO-177#comment",
            "createdAt": "2026-05-04T00:00:00.000Z",
            "updatedAt": "2026-05-04T00:00:00.000Z",
            "issue": {"id": "issue-1", "identifier": "JTO-177", "title": "[webhook-ingress-canary] issue"},
        },
    }
    comment_result = ingress.handle(signed_request(payload=comment_payload, delivery_id="comment-event"))

    assert issue_result.http_status == 200
    assert comment_result.http_status == 200
    assert comments == []


def test_canary_comment_failure_still_accepts_event():
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["labels"] = [{"id": "label-1", "name": "webhook-ingress-canary"}]
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry([], fail=True),
    )

    result = ingress.handle(signed_request(payload=payload, delivery_id="canary-comment-error"))

    assert result.http_status == 200
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'linear canary comment failed' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert json.loads(row[0])["status"] == "error"


def test_duplicate_delivery_does_not_create_canary_comment():
    comments = []
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["labels"] = [{"id": "label-1", "name": "webhook-ingress-canary"}]
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=canary_registry(comments),
    )

    first = ingress.handle(signed_request(payload=payload, delivery_id="same-canary-comment-delivery"))
    second = ingress.handle(signed_request(payload=payload, delivery_id="same-canary-comment-delivery"))

    assert first.ack.to_dict()["status"] == "accepted"
    assert second.ack.to_dict()["status"] == "duplicate_accepted"
    assert comments == [first.ack.to_dict()["event_id"]]


def test_factory_dispatch_dryrun_generates_payload_for_project_ready_transition():
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["data"]["project"] = {"id": "project-1", "name": "Webhook Ingress Canary Project"}
    payload["updatedFrom"] = {"stateId": "state-prev", "state": {"id": "state-prev", "name": "Backlog"}}
    payload["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry({"project-1"}),
    )

    result = ingress.handle(signed_request(payload=payload, delivery_id="factory-dispatch-ready"))

    assert result.http_status == 200
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'factory dispatch dry-run payload generated' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    details = json.loads(row[0])
    action_result = details["action_result_json"]
    assert details["action_name"] == "factory_dispatch_dryrun"
    assert details["status"] == "success"
    assert details["project_id"] == "project-1"
    assert action_result["dispatch_mode"] == "dry_run"
    assert action_result["dispatch_type"] == "factory_main_thread"
    assert action_result["linear_issue_key"] == "JTO-177"
    assert action_result["project_id"] == "project-1"
    assert action_result["ci_required"] is True
    assert action_result["gitlab_required"] is True
    assert action_result["max_bailian_agents"] == 10
    assert action_result["min_bailian_agents"] == 1
    assert action_result["required_review_agents"] == 1
    assert action_result["main_thread_policy"]["must_not_implement_code"] is True
    assert action_result["subagent_policy"]["implementation_by_bailian_only"] is True
    assert action_result["acceptance_policy"]["gitlab_ci_must_pass"] is True
    assert action_result["loop_guard_policy"]["duplicate_webhook_not_redispatched"] is True


def test_factory_dispatch_dryrun_skips_out_of_project_non_ready_and_comment_events():
    store = WebhookEventStore()
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry({"project-1"}),
    )
    outside = linear_issue_payload()
    outside["data"]["projectId"] = "project-outside"
    outside["updatedFrom"] = {"state": {"id": "state-prev", "name": "Backlog"}}
    outside["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    non_ready = linear_issue_payload()
    non_ready["data"]["projectId"] = "project-1"
    non_ready["updatedFrom"] = {"state": {"id": "state-prev", "name": "Backlog"}}
    non_ready["data"]["state"] = {"id": "state-progress", "name": "In Progress"}
    comment_payload = {
        "type": "Comment",
        "action": "create",
        "organizationId": "org-1",
        "data": {"id": "comment-1", "body": "Ready for Factory", "createdAt": "2026-05-04T00:00:00.000Z"},
    }

    assert ingress.handle(signed_request(payload=outside, delivery_id="factory-outside")).http_status == 200
    assert ingress.handle(signed_request(payload=non_ready, delivery_id="factory-non-ready")).http_status == 200
    assert ingress.handle(signed_request(payload=comment_payload, delivery_id="factory-comment")).http_status == 200

    rows = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'factory dispatch dry-run payload generated'"
    ).fetchall()
    assert rows == []


def test_factory_dispatch_duplicate_delivery_does_not_regenerate_payload():
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["updatedFrom"] = {"state": {"id": "state-prev", "name": "Backlog"}}
    payload["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry({"project-1"}),
    )

    first = ingress.handle(signed_request(payload=payload, delivery_id="factory-duplicate"))
    second = ingress.handle(signed_request(payload=payload, delivery_id="factory-duplicate"))

    assert first.ack.to_dict()["status"] == "accepted"
    assert second.ack.to_dict()["status"] == "duplicate_accepted"
    rows = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'factory dispatch dry-run payload generated'"
    ).fetchall()
    assert len(rows) == 1


def test_shadow_route_mode_does_not_forward():
    forwarded = []
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store, n8n_sender=forwarded.append, route_mode="shadow")
    result = ingress.handle(signed_request(delivery_id="shadow-delivery"))

    assert result.http_status == 200
    assert result.forwarded_to_n8n is False
    assert forwarded == []
    assert store.count("webhook_raw_events") == 1
    assert store.count("webhook_canonical_events") == 1


def test_signature_invalid_ack_and_no_raw_storage():
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store)
    req = signed_request()
    bad = WebhookRequest(provider="linear", raw_body=req.raw_body, headers={"Linear-Signature": "bad"}, path="/webhooks/linear")
    result = ingress.handle(bad)

    assert result.http_status == 401
    assert result.ack.to_dict()["ok"] is False
    assert result.ack.to_dict()["status"] == "SIGNATURE_INVALID"
    assert result.ack.to_dict()["error"] == "SIGNATURE_INVALID"
    assert store.count("webhook_raw_events") == 0
    assert store.count("webhook_canonical_events") == 0


def test_duplicate_event_returns_duplicate_accepted_and_does_not_forward_again():
    forwarded = []
    store = WebhookEventStore()
    ingress = WebhookIngress(linear_secret=SECRET, store=store, n8n_sender=forwarded.append)
    first = ingress.handle(signed_request(delivery_id="same-delivery"))
    second = ingress.handle(signed_request(delivery_id="same-delivery"))

    assert first.http_status == 200
    assert first.ack.to_dict()["status"] == "accepted"
    assert second.http_status == 200
    assert second.ack.to_dict()["status"] == "duplicate_accepted"
    assert second.ack.to_dict()["event_id"] == first.ack.to_dict()["event_id"]
    assert store.count("webhook_raw_events") == 1
    assert store.count("webhook_canonical_events") == 1
    assert len(forwarded) == 1


def test_idempotency_falls_back_to_raw_body_sha256_without_delivery_id():
    adapter = LinearAdapter(SECRET)
    req = signed_request(delivery_id="")
    req = WebhookRequest(provider="linear", raw_body=req.raw_body, headers={"Linear-Signature": req.header("Linear-Signature") or ""}, path=req.path)
    event = adapter.normalize(req)
    assert event["idempotency_key"].startswith("linear:sha256:")


def test_routing_by_canonical_event():
    matcher = RouteMatcher()
    created = {"provider": "linear", "canonical_type": "issue", "canonical_action": "created"}
    updated = {"provider": "linear", "canonical_type": "issue", "canonical_action": "updated"}
    comment = {"provider": "linear", "canonical_type": "comment", "canonical_action": "created"}
    assert matcher.match(created).endswith("/webhook/linear-issue-created")
    assert matcher.match(updated).endswith("/webhook/linear-issue-updated")
    assert matcher.match(comment).endswith("/webhook/linear-comment-events")
    assert matcher.ingress_path("linear") == "/webhooks/linear"


# === P1 dry-run dispatch acceptance tests ===

P1_REQUIRED_PAYLOAD_FIELDS = [
    "dry_run", "no_write", "no_push", "no_deploy",
    "github_push_forbidden", "required_ci", "parent_droid_role",
    "stop_condition", "gitlab_required", "max_fix_attempts",
    "subagent_policy", "dispatch_id", "linear_issue_key",
    "project_id", "title",
]

P1_REQUIRED_COMMENT_MARKERS = [
    "Factory dispatch dry-run generated",
    "No real Factory task was triggered",
    "No GitHub push",
    "GitLab CI required before real execution",
    "secret scan = 0 findings",
]


def _p1_factory_dispatch_event(allowed_project_ids=None):
    """Helper: run factory dispatch dry-run and return action_result_json."""
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["data"]["project"] = {"id": "project-1", "name": "Webhook Ingress Canary Project"}
    payload["updatedFrom"] = {"stateId": "state-prev", "state": {"id": "state-prev", "name": "Backlog"}}
    payload["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    ingress = WebhookIngress(
        linear_secret=SECRET,
        store=store,
        n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry(allowed_project_ids or {"project-1"}),
    )
    result = ingress.handle(signed_request(payload=payload, delivery_id=f"p1-test-{id(payload)}"))
    return result, store


def test_p1_canary_issue_dispatch_payload_generated():
    """P1 scenario 1: Linear canary issue event -> dispatch payload generated."""
    result, store = _p1_factory_dispatch_event()
    assert result.http_status == 200
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'factory dispatch dry-run payload generated'"
    ).fetchone()
    assert row is not None
    action_result = json.loads(row[0])["action_result_json"]
    for field in P1_REQUIRED_PAYLOAD_FIELDS:
        assert field in action_result, f"missing required field: {field}"


def test_p1_non_canary_condition_no_payload():
    """P1 scenario 2: Non-canary condition -> no payload generated."""
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    # NOT in Ready for Factory state
    payload["data"]["state"] = {"id": "state-backlog", "name": "Backlog"}
    ingress = WebhookIngress(
        linear_secret=SECRET, store=store, n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry({"project-1"}),
    )
    result = ingress.handle(signed_request(payload=payload, delivery_id="p1-non-canary"))
    assert result.http_status == 200
    rows = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE phase = 'canary_action' AND message = 'factory dispatch dry-run payload generated'"
    ).fetchall()
    assert rows == []


def test_p1_duplicate_delivery_idempotent():
    """P1 scenario 3: Duplicate delivery-id -> duplicate_accepted, no re-generation."""
    store = WebhookEventStore()
    payload = linear_issue_payload()
    payload["data"]["projectId"] = "project-1"
    payload["updatedFrom"] = {"state": {"id": "state-prev", "name": "Backlog"}}
    payload["data"]["state"] = {"id": "state-ready", "name": "Ready for Factory"}
    ingress = WebhookIngress(
        linear_secret=SECRET, store=store, n8n_sender=lambda event: None,
        route_mode="production_canary",
        action_registry=factory_dispatch_registry({"project-1"}),
    )
    first = ingress.handle(signed_request(payload=payload, delivery_id="p1-dup-delivery"))
    second = ingress.handle(signed_request(payload=payload, delivery_id="p1-dup-delivery"))
    assert first.ack.to_dict()["status"] == "accepted"
    assert second.ack.to_dict()["status"] == "duplicate_accepted"
    rows = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchall()
    assert len(rows) == 1


def test_p1_payload_safety_flags():
    """P1 scenario 4: Dispatch payload contains dry_run/no_write/no_push/no_deploy."""
    result, store = _p1_factory_dispatch_event()
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchone()
    p = json.loads(row[0])["action_result_json"]
    assert p["dry_run"] is True
    assert p["no_write"] is True
    assert p["no_push"] is True
    assert p["no_deploy"] is True


def test_p1_payload_no_secrets():
    """P1 scenario 5: Dispatch payload does not contain any secrets."""
    result, store = _p1_factory_dispatch_event()
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchone()
    payload_str = json.dumps(json.loads(row[0])["action_result_json"])
    secret_patterns = ["glpat-", "sk-", "BEGIN PRIVATE KEY", "lin_api_", "fk-", "password", "secret"]
    for pattern in secret_patterns:
        assert pattern not in payload_str, f"secret pattern found in payload: {pattern}"


def test_p1_canary_comment_no_secrets():
    """P1 scenario 6: Linear dry-run comment body does not contain secrets."""
    from workspace.tools.webhook_ingress.executors import linear_canary_comment_body
    test_event = {
        "event_id": "evt_p1_test",
        "idempotency_key": "linear:delivery-p1",
        "source": {"resource_id": "issue-p1"},
        "payload": {"identifier": "JTO-999"},
    }
    body = linear_canary_comment_body(test_event)
    secret_patterns = ["glpat-", "sk-", "BEGIN PRIVATE KEY", "lin_api_", "fk-", "password"]
    for pattern in secret_patterns:
        assert pattern not in body, f"secret pattern in comment: {pattern}"
    for marker in P1_REQUIRED_COMMENT_MARKERS:
        assert marker in body, f"missing required marker in comment: {marker}"


def test_p1_production_issue_not_triggered():
    """P1 scenario 7: Production issue (outside allowed projects) is not triggered."""
    result, store = _p1_factory_dispatch_event(allowed_project_ids={"project-allowed"})
    assert result.http_status == 200
    rows = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchall()
    assert rows == []


def test_p1_github_push_forbidden_policy():
    """P1 scenario 8: github_push_forbidden policy exists in payload."""
    result, store = _p1_factory_dispatch_event()
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchone()
    p = json.loads(row[0])["action_result_json"]
    assert p["github_push_forbidden"] is True


def test_p1_gitlab_required_policy():
    """P1 scenario 9: GitLab required policy exists in payload."""
    result, store = _p1_factory_dispatch_event()
    row = store.conn.execute(
        "SELECT details FROM webhook_processing_logs WHERE message = 'factory dispatch dry-run payload generated'"
    ).fetchone()
    p = json.loads(row[0])["action_result_json"]
    assert p["gitlab_required"] is True
    assert p["required_ci"] == "gitlab"
    assert p["stop_condition"]["no_real_factory_dispatch_in_p1"] is True
