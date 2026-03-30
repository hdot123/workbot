#!/usr/bin/env python3
"""Compatibility CLI that reads and initializes the canonical runtime ledger."""

from __future__ import annotations

import argparse
import json
from typing import Any

from runtime_ledger import (
    CURRENT_RUNTIME_LEDGER_PATH,
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    DEFAULT_WORKER_CEILING,
    init_current_runtime_ledger,
    load_current_runtime_ledger,
    parse_slot_binding_entry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility helper for tmux runtime ledger. "
            "Writes to canonical current-runtime.json."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize canonical runtime ledger.")
    init_parser.add_argument("--task-id", default="legacy-compat", help="Task identifier.")
    init_parser.add_argument(
        "--pane-count",
        type=int,
        default=DEFAULT_FORMAL_PANE_COUNT,
        help="Current pane count.",
    )
    init_parser.add_argument("--topology-fingerprint", default="", help="Current topology fingerprint.")
    init_parser.add_argument(
        "--formal-session-name",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help="Single official formal session name.",
    )
    init_parser.add_argument(
        "--slot-binding",
        action="append",
        default=[],
        help="slot=pane_title@target binding. Repeatable.",
    )
    init_parser.add_argument("--runtime-status", default="INIT_IN_PROGRESS", help="Initial runtime status.")
    init_parser.add_argument(
        "--watcher-armed",
        action="store_true",
        help="Mark watcher as armed in the initial ledger.",
    )
    init_parser.add_argument(
        "--watcher-target",
        action="append",
        default=[],
        help="Watcher target to store in the initial ledger. Repeatable.",
    )
    init_parser.add_argument("--watcher-pid", type=int, help="Watcher pid, if already known.")
    init_parser.add_argument(
        "--codex-thread-bound",
        dest="codex_thread_bound",
        action="store_true",
        help="Mark CODEX_THREAD_ID as already bound in the initial ledger.",
    )
    init_parser.add_argument(
        "--worker-ceiling",
        type=int,
        default=DEFAULT_WORKER_CEILING,
        help="Concurrent worker ceiling.",
    )
    init_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    read_parser = subparsers.add_parser("read", help="Read canonical runtime ledger.")
    read_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def parse_slot_bindings(items: list[str]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for entry in items:
        slot_name, binding = parse_slot_binding_entry(entry)
        bindings[slot_name] = binding
    return bindings


def main() -> int:
    args = parse_args()
    if args.command == "init":
        ledger = init_current_runtime_ledger(
            task_id=args.task_id,
            pane_count=args.pane_count,
            topology_fingerprint=args.topology_fingerprint,
            formal_session_name=args.formal_session_name,
            slot_bindings=parse_slot_bindings(args.slot_binding),
            watcher={
                "armed": bool(args.watcher_armed),
                "targets": args.watcher_target,
                "pid": args.watcher_pid,
                "transport": "codex",
            },
            codex_thread_bound=args.codex_thread_bound,
            runtime_status=args.runtime_status,
            worker_ceiling=args.worker_ceiling,
        )
        print(f"Created ledger at {CURRENT_RUNTIME_LEDGER_PATH}")
        if args.pretty:
            print(json.dumps(ledger, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(ledger, ensure_ascii=False))
        return 0

    if args.command == "read":
        ledger: dict[str, Any] = load_current_runtime_ledger()
        if not ledger:
            raise FileNotFoundError(f"ledger not found at {CURRENT_RUNTIME_LEDGER_PATH}")
        if args.pretty:
            print(json.dumps(ledger, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(ledger, ensure_ascii=False))
        return 0

    raise SystemExit("invalid command")


if __name__ == "__main__":
    raise SystemExit(main())
