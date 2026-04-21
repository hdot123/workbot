#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_full_workflow_log import (
    DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME,
    MAIN_THREAD_DIRECT_REJECT_KIND,
    append_main_thread_action,
)


def parse_details_json(rendered: str) -> dict[str, Any] | None:
    if not rendered.strip():
        return None
    payload = json.loads(rendered)
    if not isinstance(payload, dict):
        raise ValueError("--details-json must decode to a JSON object")
    return payload


def parse_task_source_json(rendered: str) -> dict[str, Any] | None:
    if not rendered.strip():
        return None
    payload = json.loads(rendered)
    if not isinstance(payload, dict):
        raise ValueError("--task-source-json must decode to a JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a formal main-thread A8/A9 action and refresh the live cmux workflow log."
    )
    parser.add_argument(
        "--runtime-dir",
        default="/Users/busiji/workbot/workspace/artifacts/cmux-runtime",
        help="cmux runtime artifact directory",
    )
    parser.add_argument("--phase", default="", help="formal lifecycle phase, usually A8 or A9")
    parser.add_argument(
        "--kind",
        default="",
        choices=(
            "main_thread_acceptance",
            "main_thread_closure",
            "main_thread_review",
            MAIN_THREAD_DIRECT_REJECT_KIND,
        ),
        help="formal main-thread action kind",
    )
    parser.add_argument("--summary", default="", help="short commander-facing action summary")
    parser.add_argument("--logical-target", default="", help="optional logical target such as pm-bot")
    parser.add_argument("--assignment-id", default="", help="optional assignment id")
    parser.add_argument("--round-id", default="", help="optional round id")
    parser.add_argument("--at", default="", help="optional explicit timestamp; defaults to now")
    parser.add_argument(
        "--direct-reject",
        action="store_true",
        help="record an explicit A9 main_thread_direct_reject entry",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="optional reject reason; primarily used with --direct-reject",
    )
    parser.add_argument(
        "--details-json",
        default="",
        help="optional JSON object string stored under details",
    )
    parser.add_argument(
        "--task-source-json",
        default="",
        help="optional current task source JSON object; when omitted the tool derives it from cmux-assignment.json",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="optional explicit output path for the refreshed live workflow log",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    details = parse_details_json(args.details_json)
    task_source_ref = parse_task_source_json(args.task_source_json)
    phase = args.phase
    kind = args.kind
    summary = args.summary.strip()

    if args.direct_reject:
        if kind and kind != MAIN_THREAD_DIRECT_REJECT_KIND:
            parser.error("--direct-reject cannot be combined with a non-direct-reject --kind")
        if phase and phase.strip().upper() != "A9":
            parser.error("--direct-reject must use phase A9")
        if details is None:
            details = {}
        if args.reason.strip():
            details.setdefault("reason", args.reason.strip())
        phase = "A9"
        kind = MAIN_THREAD_DIRECT_REJECT_KIND
        summary = summary or f"main-thread direct rejected the current run: {args.reason.strip() or 'reason not provided'}"
    else:
        if not phase:
            parser.error("--phase is required unless --direct-reject is used")
        if not kind:
            parser.error("--kind is required unless --direct-reject is used")
        if not summary:
            parser.error("--summary is required unless --direct-reject is used")

    output_path = append_main_thread_action(
        runtime_dir,
        phase=phase,
        kind=kind,
        summary=summary,
        logical_target=args.logical_target,
        assignment_id=args.assignment_id,
        round_id=args.round_id,
        task_source_ref=task_source_ref,
        details=details,
        at=args.at or None,
        output_path=args.output_json or None,
    )
    print(
        json.dumps(
            {
                "runtime_dir": str(runtime_dir),
                "journal_file": str(runtime_dir / DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME),
                "output_json": str(output_path),
                "kind": kind,
                "phase": phase,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
