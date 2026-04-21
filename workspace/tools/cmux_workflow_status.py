#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_full_workflow_log import (
    DEFAULT_LIVE_JSON_NAME,
    DEFAULT_LIVE_SUMMARY_NAME,
    materialize_live_workflow_log,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a commander-friendly status view for the current cmux workflow."
    )
    parser.add_argument(
        "--runtime-dir",
        default="/Users/busiji/workbot/workspace/artifacts/cmux-runtime",
        help="cmux runtime artifact directory",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="read the current summary artifact without rematerializing workflow artifacts first",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the commander summary artifact as JSON instead of a compact text view",
    )
    return parser


def render_text(summary: dict[str, object], runtime_dir: Path) -> str:
    missing_evidence = summary.get("missing_evidence") or []
    if not isinstance(missing_evidence, list):
        missing_evidence = []
    hard_gap_reasons = summary.get("hard_gap_reasons") or []
    if not isinstance(hard_gap_reasons, list):
        hard_gap_reasons = []
    direct_reject_details = summary.get("direct_reject_details") or []
    if not isinstance(direct_reject_details, list):
        direct_reject_details = []
    detail_path = summary.get("primary_sidecar_path") or str(runtime_dir / DEFAULT_LIVE_JSON_NAME)
    archive_dir = summary.get("archive_bundle_dir") or ""
    lines = [
        (
            f"phase={summary.get('current_phase') or 'unknown'} "
            f"status={summary.get('current_state') or summary.get('status') or 'unknown'} "
            f"outcome={summary.get('outcome') or 'unknown'}"
        ),
        f"task={summary.get('assignment_id') or 'none'} target={summary.get('logical_target') or 'none'} active={summary.get('active_assignment_count') or 0}",
        f"next={summary.get('next_action') or 'none'}",
        f"missing={', '.join(str(item) for item in missing_evidence) if missing_evidence else 'none'}",
        f"hard_gaps={', '.join(str(item) for item in hard_gap_reasons) if hard_gap_reasons else 'none'}",
        f"summary={runtime_dir / DEFAULT_LIVE_SUMMARY_NAME}",
        f"detail={detail_path}",
    ]
    if direct_reject_details:
        first_detail = direct_reject_details[0] if isinstance(direct_reject_details[0], dict) else {}
        lines.append(f"direct_reject={first_detail.get('reason') or 'recorded'}")
    if archive_dir:
        lines.append(f"archive={archive_dir}")
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    if not args.no_refresh:
        materialize_live_workflow_log(runtime_dir)
    summary_path = runtime_dir / DEFAULT_LIVE_SUMMARY_NAME
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary, runtime_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
