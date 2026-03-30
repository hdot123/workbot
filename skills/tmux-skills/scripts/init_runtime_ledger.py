#!/usr/bin/env python3
"""Initialize the current tmux-skills runtime ledger."""

from __future__ import annotations

import argparse
import json

from runtime_ledger import (
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    DEFAULT_WORKER_CEILING,
    init_current_runtime_ledger,
    parse_slot_binding_entry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the tmux-skills current runtime ledger.")
    parser.add_argument("--task-id", required=True, help="Task identifier for the current runtime.")
    parser.add_argument(
        "--pane-count",
        type=int,
        default=DEFAULT_FORMAL_PANE_COUNT,
        help="Current formal pane count.",
    )
    parser.add_argument("--topology-fingerprint", default="", help="Current topology fingerprint.")
    parser.add_argument(
        "--formal-session-name",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help="Single official formal session name.",
    )
    parser.add_argument("--runtime-status", default="INIT_IN_PROGRESS", help="Initial runtime status.")
    parser.add_argument(
        "--slot-binding",
        action="append",
        default=[],
        help="Assign a slot binding using slot=pane_title@target syntax. Repeatable.",
    )
    parser.add_argument(
        "--slot-bindings-json",
        default="",
        help="Optional JSON object describing slot bindings.",
    )
    parser.add_argument(
        "--watcher-armed",
        action="store_true",
        help="Mark watcher as armed in the initial ledger.",
    )
    parser.add_argument(
        "--watcher-target",
        action="append",
        default=[],
        help="Watcher target to store in the initial ledger. Repeatable.",
    )
    parser.add_argument("--watcher-pid", type=int, help="Watcher pid, if already known.")
    parser.add_argument(
        "--codex-thread-bound",
        dest="codex_thread_bound",
        action="store_true",
        help="Mark CODEX_THREAD_ID as already bound in the initial ledger.",
    )
    parser.add_argument(
        "--worker-ceiling",
        type=int,
        default=DEFAULT_WORKER_CEILING,
        help="Concurrent worker ceiling.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the output.")
    return parser.parse_args()


def parse_slot_bindings(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    if args.slot_bindings_json:
        payload = json.loads(args.slot_bindings_json)
        if not isinstance(payload, dict):
            raise ValueError("slot-bindings-json must describe an object")
        for slot_name, binding in payload.items():
            if not isinstance(binding, dict):
                raise ValueError("slot-bindings-json values must be objects")
            bindings[str(slot_name).strip()] = {
                "pane_title": str(binding.get("pane_title", "")).strip(),
                "target": str(binding.get("target", "")).strip(),
            }
    for entry in args.slot_binding:
        slot_name, binding = parse_slot_binding_entry(entry)
        bindings[slot_name] = binding
    return bindings


def build_watcher(args: argparse.Namespace) -> dict[str, object]:
    watcher: dict[str, object] = {
        "armed": bool(args.watcher_armed),
        "targets": [target.strip() for target in args.watcher_target if str(target).strip()],
    }
    if args.watcher_pid is not None:
        watcher["pid"] = args.watcher_pid
    watcher["transport"] = "codex"
    return watcher


def main() -> int:
    args = parse_args()
    ledger = init_current_runtime_ledger(
        task_id=args.task_id,
        pane_count=args.pane_count,
        topology_fingerprint=args.topology_fingerprint,
        formal_session_name=args.formal_session_name,
        slot_bindings=parse_slot_bindings(args),
        watcher=build_watcher(args),
        codex_thread_bound=args.codex_thread_bound,
        runtime_status=args.runtime_status,
        worker_ceiling=args.worker_ceiling,
    )
    if args.pretty:
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(ledger, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
