#!/usr/bin/env python3
"""Phase-4 verification executor for tmux-skills."""

from __future__ import annotations

import argparse
import json

from check_tmux_ready import evaluate, resolve_formal_session_name
from tmux_runtime_common import inspect_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the current tmux-skills runtime end-to-end.")
    parser.add_argument("--expected-pane-count", type=int, help="Expected pane count for the runtime.")
    parser.add_argument("--require-formal", action="store_true", help="Require the single formal non-bootstrap session.")
    parser.add_argument("--require-bell", action="store_true", help="Require the doorbell runtime to be armed.")
    parser.add_argument("--allow-bootstrap", action="store_true", help="Allow bootstrap-only status.")
    parser.add_argument(
        "--allow-informal",
        action="store_true",
        help="Allow the verification to run before the formal sessions exist.",
    )
    parser.add_argument(
        "--allow-unarmed-bell",
        action="store_true",
        help="Allow running without the doorbell runtime being armed.",
    )
    parser.add_argument(
        "--allow-extra-formal-sessions",
        action="store_true",
        help="Deprecated and ignored: runtime now requires exactly one formal session.",
    )
    parser.add_argument(
        "--formal-session-name",
        default="formal-session",
        help="Single formal session name required during verification.",
    )
    parser.add_argument(
        "--task-session-name",
        default="",
        help="Deprecated alias for --formal-session-name.",
    )
    parser.add_argument(
        "--monitor-session-name",
        default="",
        help="Deprecated alias for --formal-session-name.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.require_formal = args.require_formal or not args.allow_informal
    args.require_bell = args.require_bell or not args.allow_unarmed_bell

    snapshot = inspect_runtime(resolve_formal_session_name(args))
    result = evaluate(snapshot, args)
    result["phase"] = "verify"
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["runtime_status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
