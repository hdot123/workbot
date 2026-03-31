#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: Integrated into tmux_runtime_common.py
# Alternative: Use tmux_runtime_common.inspect_runtime() instead
# This file is retained for backward compatibility only.
# ==============================================================================

"""Inspect the current Workbot tmux runtime and print a JSON snapshot (DEPRECATED)."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("inspect_tmux_runtime.py")
# ==============================================================================

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
