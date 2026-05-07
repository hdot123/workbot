from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dispatch_payload import FactoryDispatchPayloadBuilder


@dataclass(frozen=True)
class LinearCanaryCommentResult:
    comment_id: str | None


@dataclass(frozen=True)
class FactoryDispatchDryRunResult:
    action_result_json: dict[str, Any]


class FactoryDispatchDryRunExecutor:
    def __init__(self, *, payload_builder: FactoryDispatchPayloadBuilder):
        self.payload_builder = payload_builder

    def execute(self, canonical_event: dict[str, Any]) -> FactoryDispatchDryRunResult:
        return FactoryDispatchDryRunResult(action_result_json=self.payload_builder.build(canonical_event))


class LinearCanaryCommentExecutor:
    def __init__(self, *, api_token: str, timeout: int = 10):
        if not api_token:
            raise RuntimeError("LINEAR_CANARY_API_TOKEN is not set")
        import httpx

        self._api_token = api_token
        self._client = httpx.Client(timeout=timeout)

    def execute(self, canonical_event: dict[str, Any]) -> LinearCanaryCommentResult:
        issue_id = canonical_event["source"]["resource_id"]
        query = """
        mutation CanaryComment($issueId: String!, $body: String!) {
          commentCreate(input: {issueId: $issueId, body: $body}) {
            success
            comment { id }
          }
        }
        """
        response = self._client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": self._api_token, "Content-Type": "application/json"},
            json={"query": query, "variables": {"issueId": issue_id, "body": linear_canary_comment_body(canonical_event)}},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError("Linear commentCreate returned errors")
        result = data.get("data", {}).get("commentCreate") or {}
        if not result.get("success"):
            raise RuntimeError("Linear commentCreate was not successful")
        comment = result.get("comment") or {}
        return LinearCanaryCommentResult(comment_id=comment.get("id"))


def linear_canary_comment_body(canonical_event: dict[str, Any]) -> str:
    payload = canonical_event.get("payload") or {}
    identifier = payload.get("identifier") or canonical_event["source"]["resource_id"]
    return f"[webhook-ingress-canary] OPS-LINEAR-010 canonical event {canonical_event['event_id']} accepted for {identifier}."
