#!/usr/bin/env python3
"""tmux-skills verification wrapper."""

from __future__ import annotations

import argparse
import json

from check_tmux_ready import evaluate
from tmux_runtime_common import inspect_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the current tmux-skills runtime end-to-end.")
    parser.add_argument("--expected-pane-count", type=int, help="Expected pane count for the runtime.")
    parser.add_argument(
        "--formal-session-name",
        default="formal-session",
        help="Formal session name required during verification.",
    )
    parser.add_argument("--require-formal", action="store_true", help="Require the single formal session.")
    parser.add_argument(
        "--require-watcher",
        action="store_true",
        help="Require the tmux-skills watcher to be armed.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = inspect_runtime(args.formal_session_name)
    result = evaluate(snapshot, args)
    result["phase"] = "verify"
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["runtime_status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
