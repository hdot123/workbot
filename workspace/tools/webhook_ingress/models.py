from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class WebhookRequest:
    provider: str
    raw_body: bytes
    headers: Mapping[str, str]
    path: str = ""
    source_ip: str | None = None

    def header(self, name: str) -> str | None:
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return None


@dataclass(frozen=True)
class AckResponse:
    ok: bool
    status: str
    request_id: str
    event_id: str | None
    provider: str
    error: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        body: dict[str, str | bool | None] = {
            "ok": self.ok,
            "status": self.status,
            "request_id": self.request_id,
            "event_id": self.event_id,
            "provider": self.provider,
        }
        if self.error:
            body["error"] = self.error
        return body
