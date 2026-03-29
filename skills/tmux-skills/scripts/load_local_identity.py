#!/usr/bin/env python3
"""Load local fixed identities for the first tmux-skills phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


IDENTITY_CATALOG_PATH = Path("/Users/busiji/workbot/skills/tmux-skills/identities/catalog.json")
REQUIRED_FIELDS = {
    "identity_id",
    "identity_name",
    "identity_version",
    "role_type",
    "model",
    "source_file",
    "constraints",
    "output_contract",
    "status",
}


def load_catalog() -> dict[str, Any]:
    if not IDENTITY_CATALOG_PATH.exists():
        raise FileNotFoundError(f"identity catalog not found: {IDENTITY_CATALOG_PATH}")
    data = json.loads(IDENTITY_CATALOG_PATH.read_text(encoding="utf-8"))
    identities = data.get("identities")
    if not isinstance(identities, list):
        raise ValueError("identity catalog must contain an identities list")
    return data


def validate_identity(identity: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - identity.keys())
    if missing:
        raise ValueError(f"identity {identity.get('identity_id', '<unknown>')} missing fields: {missing}")
    source_file = Path(identity["source_file"])
    if not source_file.exists():
        raise FileNotFoundError(f"identity source file not found: {source_file}")


def list_identities() -> list[dict[str, Any]]:
    catalog = load_catalog()
    identities = catalog["identities"]
    for identity in identities:
        validate_identity(identity)
    return identities


def resolve_identity(identity_id: str) -> dict[str, Any]:
    for identity in list_identities():
        if identity["identity_id"] != identity_id:
            continue
        resolved = dict(identity)
        source_path = Path(identity["source_file"])
        resolved["system_prompt"] = source_path.read_text(encoding="utf-8")
        resolved["catalog_path"] = str(IDENTITY_CATALOG_PATH)
        return resolved
    raise KeyError(f"identity not found: {identity_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load tmux-skills local fixed identities.")
    parser.add_argument("--identity-id", help="Resolve one identity by identity_id.")
    parser.add_argument("--list", action="store_true", help="List available identities.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.identity_id:
        payload: Any = resolve_identity(args.identity_id)
    else:
        payload = [
            {
                "identity_id": identity["identity_id"],
                "identity_name": identity["identity_name"],
                "identity_version": identity["identity_version"],
                "role_type": identity["role_type"],
                "status": identity["status"],
                "source_file": identity["source_file"],
            }
            for identity in list_identities()
        ]
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
