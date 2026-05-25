from __future__ import annotations

REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "authorization",
    "signature",
    "secret",
    "token",
    "password",
    "key",
    "cookie",
)


def is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(part in lower for part in SENSITIVE_KEY_PARTS)


def redact_mapping(values: dict[str, object]) -> dict[str, object]:
    return {key: REDACTED if is_sensitive_key(key) else value for key, value in values.items()}
