#!/usr/bin/env python3
"""Run the formal tmux-skills runtime-only chain with strict defaults."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from runtime_ledger import (
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    DEFAULT_FORMAL_PANE_TITLES,
    DEFAULT_WORKER_CEILING,
    build_slot_bindings_from_targets,
)


ROOT = Path("/Users/busiji/workbot")
SCRIPTS_DIR = ROOT / "skills" / "tmux-skills" / "scripts"

ENV_SCRIPT = SCRIPTS_DIR / "init_tmux_env.py"
TOPOLOGY_SCRIPT = SCRIPTS_DIR / "build_tmux_topology.py"
PANE_INIT_SCRIPT = SCRIPTS_DIR / "init_tmux_panes.py"
INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_tmux_runtime.py"
LEDGER_SCRIPT = SCRIPTS_DIR / "init_runtime_ledger.py"
WATCHER_SCRIPT = SCRIPTS_DIR / "arm_tmux_handoff_watcher.py"
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_tmux_runtime.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strict tmux-skills formal chain: env -> topology -> ledger -> watcher -> verify"
    )
    parser.add_argument(
        "--codex-thread-id",
        required=True,
        help="CODEX_THREAD_ID injected into tmux global environment.",
    )
    parser.add_argument(
        "--formal-session",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help=f"Formal tmux session name. Defaults to {DEFAULT_FORMAL_SESSION_NAME}.",
    )
    parser.add_argument(
        "--pane-count",
        type=int,
        help="Formal pane count. Defaults to the number of pane titles provided.",
    )
    parser.add_argument(
        "--pane-title",
        action="append",
        dest="pane_titles",
        default=[],
        help="Formal pane title. Repeat to define the pane title sequence.",
    )
    parser.add_argument(
        "--task-id",
        default="start-day-formal-runtime",
        help="Runtime ledger task id.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print result JSON.")
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_json(command: list[str], *, step: str) -> dict[str, Any]:
    proc = run(command)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "command failed").strip()
        raise RuntimeError(f"{step} failed: {detail}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{step} returned non-JSON output: {exc}") from exc


def ensure_attached_formal_session(snapshot: dict[str, Any], formal_session: str) -> None:
    for session in snapshot.get("sessions", []):
        if session.get("session_name") != formal_session:
            continue
        if int(session.get("attached", 0)) > 0:
            return
        break
    raise RuntimeError(
        f"formal session '{formal_session}' is not attached; attach it before running start-day"
    )


def parse_target(target: str) -> tuple[int, int]:
    pane = target.split(":", 1)[1]
    window_index, pane_index = pane.split(".", 1)
    return int(window_index), int(pane_index)


def select_formal_targets(snapshot: dict[str, Any], formal_session: str) -> list[str]:
    panes = [
        pane
        for pane in snapshot.get("panes", [])
        if pane.get("session_name") == formal_session
    ]
    panes.sort(key=lambda pane: parse_target(str(pane.get("target", ""))))
    return [str(pane.get("target", "")).strip() for pane in panes if str(pane.get("target", "")).strip()]


def resolve_pane_titles(args: argparse.Namespace) -> list[str]:
    explicit = [str(title).strip() for title in args.pane_titles if str(title).strip()]
    return explicit or list(DEFAULT_FORMAL_PANE_TITLES)


def build_batch_plan(targets: list[str], pane_titles: list[str]) -> list[dict[str, str]]:
    if len(targets) != len(pane_titles):
        raise RuntimeError(
            f"formal runtime must expose exactly {len(pane_titles)} panes; got {len(targets)}"
        )
    slot_bindings = build_slot_bindings_from_targets(targets, pane_titles)
    plan: list[dict[str, str]] = []
    for target, role in zip(targets, pane_titles):
        slot_name = next(
            binding_slot
            for binding_slot, binding in slot_bindings.items()
            if binding["target"] == target
        )
        plan.append(
            {
                "target": target,
                "slot": slot_name,
                "pane_title": role,
            }
        )
    return plan


def build_slot_binding_args(plan_entries: list[dict[str, str]]) -> list[str]:
    args: list[str] = []
    for entry in plan_entries:
        args.extend(
            [
                "--slot-binding",
                f"{entry['slot']}={entry['pane_title']}@{entry['target']}",
            ]
        )
    return args


def build_result(
    status: str,
    steps: dict[str, Any],
    pane_titles: list[str],
    error: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "formal_session": steps.get("formal_session", DEFAULT_FORMAL_SESSION_NAME),
        "pane_count": len(pane_titles),
        "worker_ceiling": DEFAULT_WORKER_CEILING,
        "roles": pane_titles,
        "chain": ["env", "topology", "ledger", "watcher", "verify"],
        "steps": steps,
    }
    if error:
        result["error"] = error
    return result


def main() -> int:
    args = parse_args()
    pane_titles = resolve_pane_titles(args)
    pane_count = args.pane_count or len(pane_titles)
    if pane_count != len(pane_titles):
        sys.stderr.write(
            f"pane-count must be {len(pane_titles)} for formal runtime (got {pane_count})\n"
        )
        return 2

    steps: dict[str, Any] = {"formal_session": args.formal_session}
    try:
        set_env_proc = run(
            ["tmux", "set-environment", "-g", "CODEX_THREAD_ID", args.codex_thread_id]
        )
        if set_env_proc.returncode != 0:
            detail = (set_env_proc.stderr or set_env_proc.stdout or "tmux set-environment failed").strip()
            raise RuntimeError(detail)
        steps["thread_binding"] = {"CODEX_THREAD_ID": args.codex_thread_id}

        steps["env"] = run_json(
            [
                sys.executable,
                str(ENV_SCRIPT),
                "--formal-session",
                args.formal_session,
                "--kill-detached",
                "--initialize-formal-surfaces",
                "--formal-window-title",
                args.formal_session,
                "--pretty",
            ],
            step="env",
        )

        inspect_after_env = run_json(
            [sys.executable, str(INSPECT_SCRIPT), "--pretty"],
            step="inspect_after_env",
        )
        ensure_attached_formal_session(inspect_after_env, args.formal_session)
        steps["inspect_after_env"] = {
            "formal_session_count": inspect_after_env.get("formal_session_count"),
            "attached_formal": True,
        }

        steps["topology"] = run_json(
            [
                sys.executable,
                str(TOPOLOGY_SCRIPT),
                "--formal-session",
                args.formal_session,
                "--target-pane-count",
                str(pane_count),
                "--pretty",
            ],
            step="topology",
        )

        inspect_after_topology = run_json(
            [sys.executable, str(INSPECT_SCRIPT), "--pretty"],
            step="inspect_after_topology",
        )
        targets = select_formal_targets(inspect_after_topology, args.formal_session)
        batch_plan = build_batch_plan(targets, pane_titles)
        steps["inspect_after_topology"] = {"targets": targets}

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="tmux-runtime-only-plan-",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(batch_plan, handle, ensure_ascii=False, indent=2)
            plan_path = handle.name

        scene_validation = run_json(
            [
                sys.executable,
                str(PANE_INIT_SCRIPT),
                "--batch-file",
                plan_path,
                "--pretty",
            ],
            step="existing-scene-validation",
        )
        steps["scene_validation"] = scene_validation
        if not bool(scene_validation.get("verified")):
            raise RuntimeError(
                "formal runtime requires existing whitelist Claude scenes in every pane; "
                "prepare those scenes before running start-day"
            )

        topology_fingerprint = str(inspect_after_topology.get("topology_fingerprint", "")).strip()
        if not topology_fingerprint:
            raise RuntimeError("inspect produced empty topology_fingerprint after topology")

        ledger_command = [
            sys.executable,
            str(LEDGER_SCRIPT),
            "--task-id",
            args.task_id,
            "--formal-session-name",
            args.formal_session,
            "--pane-count",
            str(pane_count),
            "--topology-fingerprint",
            topology_fingerprint,
            "--codex-thread-bound",
            "--worker-ceiling",
            str(DEFAULT_WORKER_CEILING),
            "--runtime-status",
            "INIT_IN_PROGRESS",
            "--pretty",
        ]
        ledger_command.extend(build_slot_binding_args(batch_plan))
        steps["ledger"] = run_json(ledger_command, step="ledger")

        watcher_command = [
            sys.executable,
            str(WATCHER_SCRIPT),
            "--formal-session-name",
            args.formal_session,
            "--pretty",
        ]
        for target in targets:
            watcher_command.extend(["--target", target])
        steps["watcher"] = run_json(watcher_command, step="watcher")

        steps["verify"] = run_json(
            [
                sys.executable,
                str(VERIFY_SCRIPT),
                "--formal-session-name",
                args.formal_session,
                "--expected-pane-count",
                str(pane_count),
                "--require-formal",
                "--require-bell",
                "--pretty",
            ],
            step="verify",
        )
        if steps["verify"].get("runtime_status") != "READY":
            raise RuntimeError(
                f"verify returned runtime_status={steps['verify'].get('runtime_status')}"
            )
    except Exception as exc:
        result = build_result("failed", steps, pane_titles, str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1

    result = build_result("ok", steps, pane_titles)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
