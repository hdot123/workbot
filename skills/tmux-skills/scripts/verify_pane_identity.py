#!/usr/bin/env python3
"""Verify whether a pane already hosts the expected whitelist Claude scene."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from runtime_ledger import WHITE_ROLE_TITLES
from tmux_runtime_common import is_claude_runtime_command, normalize_pane_title


def session_name_from_target(target: str) -> str:
    if ":" not in target or "." not in target.split(":", 1)[1]:
        raise ValueError(f"target must include session/window/pane: {target}")
    session_name, _, _ = target.partition(":")
    return session_name.strip()


def capture_pane(target: str, lines: int) -> str:
    proc = subprocess.run(
        ["tmux", "capture-pane", "-p", "-S", f"-{lines}", "-t", target],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to capture pane")
    return proc.stdout


def read_pane_runtime_signals(target: str) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "tmux",
            "display-message",
            "-p",
            "-t",
            target,
            "#{pane_current_command}\t#{pane_title}\t#{session_name}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or "failed to read pane runtime signals"
        )
    parts = proc.stdout.rstrip("\n").split("\t")
    if len(parts) != 3:
        raise RuntimeError("failed to parse pane runtime signals")
    pane_current_command, pane_title, session_name = parts
    normalized_title = normalize_pane_title(pane_title)
    return {
        "pane_current_command": pane_current_command.strip(),
        "pane_title": pane_title.strip(),
        "pane_title_normalized": normalized_title,
        "session_name": session_name.strip(),
        "claude_entered": is_claude_runtime_command(pane_current_command.strip()),
    }


def build_visible_markers(role: str) -> list[str]:
    role = str(role).strip()
    markers = [
        f"@{role}",
        role,
        f"已切换到 {role}",
        f"已切换到 {role}。",
        f"@{role} ·",
        f" {role} ·",
    ]
    return list(dict.fromkeys(marker for marker in markers if marker.strip()))


def evaluate_role_scene(
    content: str,
    expected_role: str,
    *,
    pane_current_command: str,
    pane_title: str,
) -> dict[str, object]:
    normalized_title = normalize_pane_title(pane_title)
    role = str(expected_role).strip()
    markers = build_visible_markers(role)
    matched_visible = [marker for marker in markers if marker in content]
    reasons: list[str] = []

    title_ok = normalized_title in WHITE_ROLE_TITLES
    if not title_ok:
        reasons.append(
            "pane title is not in whitelist: "
            f"expected one of {', '.join(WHITE_ROLE_TITLES)}, actual={normalized_title or '<empty>'}"
        )
    elif role and normalized_title != role:
        reasons.append(
            f"pane title does not match expected role: expected={role}, actual={normalized_title}"
        )
        title_ok = False

    claude_entered = is_claude_runtime_command(pane_current_command)
    if not claude_entered:
        reasons.append(
            "pane is not running Claude yet (expected node/claude runtime, "
            f"actual={pane_current_command or '<empty>'})"
        )

    scene_visible = bool(matched_visible)
    if not scene_visible:
        reasons.append("missing visible role markers in pane output")

    verified = title_ok and claude_entered and scene_visible
    return {
        "expected_role": role,
        "verified": verified,
        "title_ok": title_ok,
        "scene_visible": scene_visible,
        "claude_entered": claude_entered,
        "pane_current_command": pane_current_command,
        "matched_visible_markers": matched_visible,
        "visible_markers": markers,
        "reasons": reasons,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a pane against an existing whitelist runtime scene.")
    parser.add_argument("--target", required=True, help="tmux target such as session:window.pane")
    parser.add_argument("--role", help="Expected whitelist role title.")
    parser.add_argument("--identity-id", help="Deprecated alias for --role.")
    parser.add_argument("--lines", type=int, default=120, help="Number of lines to inspect from the pane.")
    parser.add_argument(
        "--allow-bootstrap-target",
        action="store_true",
        help="Allow bootstrap session targets (default rejects tbot).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected_role = str(args.role or args.identity_id or "").strip()
    if not expected_role:
        raise SystemExit("expected role is required (--role)")
    if expected_role not in WHITE_ROLE_TITLES:
        raise SystemExit(f"expected role must be one of: {', '.join(WHITE_ROLE_TITLES)}")
    session_name = session_name_from_target(args.target)
    if session_name == "tbot" and not args.allow_bootstrap_target:
        raise SystemExit("bootstrap target is not allowed for formal pane identity verification")
    content = capture_pane(args.target, args.lines)
    runtime_signals = read_pane_runtime_signals(args.target)
    evaluation = evaluate_role_scene(
        content,
        expected_role,
        pane_current_command=str(runtime_signals["pane_current_command"]),
        pane_title=str(runtime_signals["pane_title"]),
    )
    result = {
        "target": args.target,
        "session_name": session_name,
        "expected_role": expected_role,
        "verified": bool(evaluation["verified"]),
        "title_ok": bool(evaluation["title_ok"]),
        "scene_visible": bool(evaluation["scene_visible"]),
        "pane_current_command": runtime_signals["pane_current_command"],
        "pane_title": runtime_signals["pane_title"],
        "claude_entered": bool(evaluation["claude_entered"]),
        "reasons": evaluation["reasons"],
        "matched_visible_markers": evaluation["matched_visible_markers"],
    }
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
