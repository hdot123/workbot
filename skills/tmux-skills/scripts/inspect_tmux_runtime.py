#!/usr/bin/env python3
"""Inspect the current Workbot tmux runtime and print a JSON snapshot."""

from __future__ import annotations

import argparse
import json

from tmux_runtime_common import inspect_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the current Workbot tmux runtime.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = inspect_runtime()
    if args.pretty:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(snapshot, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
