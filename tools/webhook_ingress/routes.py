from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_ROUTES_PATH = Path(__file__).resolve().parent / "routes.yaml"


class RouteMatcher:
    def __init__(self, routes_path: str | Path | None = None):
        self.routes_path = Path(routes_path) if routes_path else DEFAULT_ROUTES_PATH
        self.config = yaml.safe_load(self.routes_path.read_text())

    def match(self, event: dict[str, Any]) -> str | None:
        provider = event["provider"]
        provider_config = self.config.get("providers", {}).get(provider)
        if not provider_config or not provider_config.get("enabled"):
            return self.config.get("default", {}).get("n8n_webhook_url")
        for route in provider_config.get("routes", []):
            criteria = route.get("match", {})
            if all(event.get(key) == value for key, value in criteria.items()):
                return route.get("n8n_webhook_url")
        return provider_config.get("n8n_webhook_url") or self.config.get("default", {}).get("n8n_webhook_url")

    def ingress_path(self, provider: str) -> str | None:
        provider_config = self.config.get("providers", {}).get(provider)
        return provider_config.get("ingress_path") if provider_config else None
