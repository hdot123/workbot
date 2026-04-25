#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: Old delivery chain has been deprecated
# Alternative: None (functionality deprecated)
# This file is retained for backward compatibility only.
# ==============================================================================

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("build_tmux_db_write_instruction.py")
# ==============================================================================

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tmux_notification_record import build_db_record, validate_db_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a tmux-runtime handoff notification event into a generic db insert instruction."
    )
    parser.add_argument(
        "--event-file",
        help="optional path to a JSON event file. If omitted, reads one JSON object from stdin.",
    )
    parser.add_argument(
        "--table",
        default="tmux_notifications_raw",
        help="target logical table name, defaults to tmux_notifications_raw",
    )
    return parser.parse_args()


def load_event(event_file: str | None) -> dict[str, Any]:
    if event_file:
        return json.loads(Path(event_file).read_text(encoding="utf-8"))
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("no event payload provided on stdin")
    return json.loads(raw)


def main() -> int:
    args = parse_args()
    try:
        event = load_event(args.event_file)
    except (ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    record = build_db_record(event)
    validation = validate_db_record(record)

    instruction = {
        "action": "db_insert",
        "table": args.table,
        "record": record,
        "validation": validation,
        "identity": {
            "identity_id": record["identity_id"],
            "identity_key": record["identity_id"],
        },
        "write_policy": {"on_invalid_identity": "drop"},
    }
    json.dump(instruction, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
