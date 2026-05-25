from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "canonical-webhook-event-v1.json"


def load_canonical_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def validate_canonical_event(event: dict[str, Any]) -> None:
    schema = load_canonical_schema()
    _validate_object(event, schema, path="$")


def _validate_object(value: Any, schema: dict[str, Any], *, path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} must equal {schema['const']!r}")
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be object")
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"{path}.{key} is required")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            extra = set(value) - allowed
            if extra:
                raise ValueError(f"{path} has unexpected keys: {sorted(extra)}")
        for key, subschema in schema.get("properties", {}).items():
            if key in value:
                _validate_object(value[key], subschema, path=f"{path}.{key}")
    elif expected_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path} must be string")
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path} is too short")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path} must be one of {schema['enum']}")
        if "pattern" in schema:
            import re
            if not re.match(schema["pattern"], value):
                raise ValueError(f"{path} does not match {schema['pattern']}")
