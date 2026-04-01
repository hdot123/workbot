#!/usr/bin/env python3
"""Watch tmux panes and report stopped or unreachable panes to the CODEX_THREAD_ID-bound Codex thread."""

# pane_stopped 统一口径：
# 1. pane_dead > 0
# 2. 首次采样只建立 baseline，不立即报停
# 3. baseline 建立后，按轮询间隔连续 3 次比较最近 5 行输出 hash 都无变化
#    默认轮询间隔为 10 秒，因此默认约 30 秒后触发 pane_stopped

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script is orchestrator_only - cannot be called directly
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_orchestrator_only
enforce_orchestrator_only("watch_tmux_handoff.py")
# ==============================================================================

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from typing import Any

from runtime_ledger import CURRENT_RUNTIME_LEDGER_PATH


DEFAULT_POLL_INTERVAL_SECONDS = 10.0
DEFAULT_CAPTURE_START = -5
DEFAULT_UNCHANGED_OUTPUT_THRESHOLD = 3
DEFAULT_DELIVERY_QUEUE_DIR = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-runtime/delivery-queue"
)
DEFAULT_DELIVERY_STDOUT_LOG = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-runtime/deliver-tmux-handoff.stdout.log"
)


def run_tmux(*args: str) -> str:
    proc = subprocess.run(
        ["tmux", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def display_value(target: str, fmt: str) -> str:
    return run_tmux("display-message", "-p", "-t", target, fmt).strip()


def capture_output(target: str, start: int) -> str:
    return run_tmux("capture-pane", "-p", "-S", str(start), "-t", target).rstrip("\n")


def resolve_target_from_pane_id(pane_id: str) -> str:
    return display_value(pane_id, "#{session_name}:#{window_index}.#{pane_index}")


def read_tmux_env(name: str) -> str:
    try:
        raw = run_tmux("show-environment", "-g", name).strip()
    except subprocess.CalledProcessError:
        return ""
    prefix = f"{name}="
    if raw.startswith(prefix):
        return raw[len(prefix) :]
    return ""


def read_tmux_session_binding() -> str:
    return read_tmux_env("CODEX_THREAD_ID")


def signature_for(payload: str) -> str:
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def event_id_for(event: dict[str, object]) -> str:
    key = "|".join(
        [
            str(event.get("event", "")),
            str(event.get("target", "")),
            str(event.get("signature", "")),
            str(event.get("detected_at", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def capture_line_count_from_start(start: int) -> int:
    if start < 0:
        return abs(start)
    return max(1, start + 1)


def capture_snapshot(target: str, start: int) -> dict[str, object]:
    recent_output = capture_output(target, start)
    recent_output_hash = signature_for(recent_output)
    session_attached = display_value(target, "#{session_attached}")
    pane_dead = display_value(target, "#{pane_dead}")
    dead_status = display_value(target, "#{pane_dead_status}")
    current_command = display_value(target, "#{pane_current_command}")
    pane_title = display_value(target, "#{pane_title}")
    cwd = display_value(target, "#{pane_current_path}")
    session_name = display_value(target, "#{session_name}")
    window_index = display_value(target, "#{window_index}")
    pane_index = display_value(target, "#{pane_index}")
    pane_id = display_value(target, "#{pane_id}")
    state_basis = "|".join(
        [
            target,
            pane_title,
            current_command,
            pane_dead,
            dead_status,
            session_attached,
            recent_output_hash,
        ]
    )
    return {
        "target": target,
        "session": session_name,
        "window": window_index,
        "pane_index": pane_index,
        "pane_id": pane_id,
        "pane_title": pane_title,
        "cwd": cwd,
        "current_command": current_command,
        "pane_dead": int(pane_dead or 0),
        "pane_dead_status": dead_status,
        "session_attached": int(session_attached or 0),
        "recent_output": recent_output,
        "recent_output_hash": recent_output_hash,
        "reachable": True,
        "state_signature": signature_for(state_basis),
    }


def classify_snapshot(snapshot: dict[str, object]) -> tuple[str, str, str] | None:
    if int(snapshot.get("session_attached", 0)) <= 0:
        return ("session_detached", "会话已脱离前台", "session_detached")
    if int(snapshot.get("pane_dead", 0)) > 0:
        status = str(snapshot.get("pane_dead_status", "")).strip()
        label = f"pane 已停止 ({status})" if status else "pane 已停止"
        return ("pane_stopped", label, "pane_stopped")
    return None


def build_state_event(
    snapshot: dict[str, object],
    *,
    event_name: str,
    state_label: str,
    state: str,
    reachable: bool,
    codex_thread_id: str,
    extra_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    event = {
        "event": event_name,
        "state_class": state,
        "state_label": state_label,
        "state": state,
        "deliverable": True,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        **snapshot,
        "reachable": reachable,
        "codex_thread_id": codex_thread_id,
        "signature": signature_for(f"{snapshot['target']}|{state}|{snapshot['state_signature']}"),
        "source": "tmux-runtime",
    }
    if extra_fields:
        event.update(extra_fields)
    event["event_id"] = event_id_for(event)
    return event


def reset_output_hash_state(
    target: str,
    *,
    last_output_hash: dict[str, str],
    unchanged_output_count: dict[str, int],
) -> None:
    last_output_hash.pop(target, None)
    unchanged_output_count.pop(target, None)


def advance_output_hash_state(
    target: str,
    snapshot: dict[str, object],
    *,
    last_output_hash: dict[str, str],
    unchanged_output_count: dict[str, int],
) -> int:
    current_hash = str(snapshot.get("recent_output_hash", "")).strip()
    previous_hash = last_output_hash.get(target, "")

    # 首次采样只建立 baseline，不计入“无变化比较”。
    if not previous_hash:
        unchanged_output_count[target] = 0
    elif current_hash == previous_hash:
        unchanged_output_count[target] = unchanged_output_count.get(target, 0) + 1
    else:
        unchanged_output_count[target] = 0

    last_output_hash[target] = current_hash
    return unchanged_output_count[target]


def build_hash_stopped_event(
    snapshot: dict[str, object],
    *,
    codex_thread_id: str,
    unchanged_count: int,
    interval_seconds: float,
    capture_lines: int,
) -> dict[str, object]:
    return build_state_event(
        snapshot,
        event_name="pane_stopped",
        state_label=(
            "pane 已停止工作"
            f"（首次采样后按 {interval_seconds:g} 秒间隔连续 {unchanged_count} 次比较无变化，"
            f"最近 {capture_lines} 行输出未变化）"
        ),
        state="pane_stopped",
        reachable=True,
        codex_thread_id=codex_thread_id,
        extra_fields={"stop_reason": "hash_unchanged_threshold"},
    )


def build_unreachable_event(
    target: str,
    *,
    reason: str,
    codex_thread_id: str,
    cached_snapshot: dict[str, object] | None = None,
) -> dict[str, object]:
    cached_snapshot = cached_snapshot or {}
    event = {
        "event": "pane_unreachable",
        "state_class": "pane_unreachable",
        "state_label": reason,
        "state": "pane_unreachable",
        "deliverable": True,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": target,
        "session": str(cached_snapshot.get("session", "")).strip() or target.partition(":")[0],
        "window": str(cached_snapshot.get("window", "")).strip() or target.partition(":")[2].partition(".")[0],
        "pane_title": str(cached_snapshot.get("pane_title", "")).strip(),
        "pane_index": str(cached_snapshot.get("pane_index", "")).strip(),
        "pane_id": str(cached_snapshot.get("pane_id", "")).strip(),
        "cwd": str(cached_snapshot.get("cwd", "")).strip(),
        "current_command": str(cached_snapshot.get("current_command", "")).strip(),
        "recent_output": str(cached_snapshot.get("recent_output", "")).strip(),
        "reachable": False,
        "codex_thread_id": codex_thread_id,
        "signature": signature_for(f"{target}|pane_unreachable|{reason}"),
        "source": "tmux-runtime",
    }
    event["event_id"] = event_id_for(event)
    return event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch tmux panes and emit stopped-pane reports."
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="tmux target, for example formal-session:1.1. Repeat for multiple panes.",
    )
    parser.add_argument(
        "--pane-id",
        action="append",
        dest="pane_ids",
        default=[],
        help="Deprecated compatibility input. Converted to target immediately.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help=f"polling interval in seconds, defaults to {DEFAULT_POLL_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=DEFAULT_CAPTURE_START,
        help=f"capture-pane start offset, defaults to {DEFAULT_CAPTURE_START}",
    )
    parser.add_argument("--once", action="store_true", help="scan once and exit")
    parser.add_argument(
        "--log-file",
        default="/Users/busiji/workbot/workspace/artifacts/tmux-runtime/handoff-notifications.jsonl",
        help="jsonl file used to record newly detected notifications",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="deliver each newly detected notification into the CODEX_THREAD_ID-bound Codex thread",
    )
    parser.add_argument(
        "--delivery-script",
        default=str(Path(__file__).with_name("deliver_tmux_handoff_notification.py")),
        help="delivery runner path, defaults to the local tmux-runtime handoff delivery script",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Codex session mode used by the handoff delivery runner, defaults to fixed",
    )
    parser.add_argument(
        "--deliver-dry-run",
        action="store_true",
        help="run the delivery runner in dry-run mode",
    )
    parser.add_argument(
        "--delivery-queue-dir",
        default=str(DEFAULT_DELIVERY_QUEUE_DIR),
        help="directory used to persist queued handoff events for the delivery runner",
    )
    parser.add_argument(
        "--delivery-stdout-log",
        default=str(DEFAULT_DELIVERY_STDOUT_LOG),
        help="stdout/stderr capture file for detached delivery runner invocations",
    )
    return parser.parse_args()


def emit(event: dict[str, object]) -> None:
    json.dump(event, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def record_event(log_file: str, event: dict[str, object]) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        json.dump(event, fh, ensure_ascii=False)
        fh.write("\n")


def delivery_queue_is_idle(queue_dir: str) -> bool:
    queue_path = Path(queue_dir)
    if not queue_path.exists():
        return True
    return not any(path.is_file() and path.suffix == ".json" for path in queue_path.iterdir())


def clear_runtime_ledger() -> None:
    try:
        CURRENT_RUNTIME_LEDGER_PATH.unlink()
    except FileNotFoundError:
        return


def queue_event(
    event: dict[str, object],
    *,
    queue_dir: str,
) -> Path:
    if not bool(event.get("deliverable")):
        raise ValueError("cannot queue a non-deliverable event")
    queue_path = Path(queue_dir)
    queue_path.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    event_id = str(event.get("event_id", "")).strip() or signature_for(
        json.dumps(event, ensure_ascii=False, sort_keys=True)
    )
    path = queue_path / f"{timestamp}-{event_id}.json"
    path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def spawn_delivery_runner(
    event_file: Path,
    *,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
    stdout_log: str,
) -> int:
    cmd = [
        sys.executable,
        delivery_script,
        "--session-mode",
        session_mode,
        "--event-file",
        str(event_file),
    ]
    if dry_run:
        cmd.append("--dry-run")
    stdout_log_path = Path(stdout_log)
    stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = stdout_log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    handle.close()
    return int(process.pid)


def handoff_event(
    event: dict[str, object],
    *,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
    queue_dir: str,
    stdout_log: str,
) -> int | None:
    if not bool(event.get("deliverable")):
        return None
    event_file = queue_event(event, queue_dir=queue_dir)
    return spawn_delivery_runner(
        event_file,
        delivery_script=delivery_script,
        session_mode=session_mode,
        dry_run=dry_run,
        stdout_log=stdout_log,
    )


def normalize_targets(args: argparse.Namespace) -> list[str]:
    targets = [str(target).strip() for target in args.targets if str(target).strip()]
    for pane_id in args.pane_ids:
        pane_id = str(pane_id).strip()
        if not pane_id:
            continue
        targets.append(resolve_target_from_pane_id(pane_id))
    targets = [target for target in targets if target]
    return sorted(dict.fromkeys(targets))


def clear_pending_event(
    target: str,
    *,
    pending_release_events: dict[str, dict[str, object]],
    pending_release_order: list[str],
) -> None:
    pending_release_events.pop(target, None)
    try:
        pending_release_order.remove(target)
    except ValueError:
        return


def queue_pending_event(
    target: str,
    event: dict[str, object],
    *,
    pending_release_events: dict[str, dict[str, object]],
    pending_release_order: list[str],
    last_report_signature: dict[str, str],
) -> None:
    signature = str(event["signature"])
    if last_report_signature.get(target) == signature:
        clear_pending_event(
            target,
            pending_release_events=pending_release_events,
            pending_release_order=pending_release_order,
        )
        return

    current_pending = pending_release_events.get(target)
    if current_pending and str(current_pending.get("signature", "")) == signature:
        return

    pending_release_events[target] = event
    if target not in pending_release_order:
        pending_release_order.append(target)


def release_event(
    event: dict[str, object],
    *,
    target: str,
    log_file: str,
    deliver: bool,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
    queue_dir: str,
    stdout_log: str,
    last_report_signature: dict[str, str],
) -> None:
    last_report_signature[target] = str(event["signature"])
    record_event(log_file, event)
    emit(event)
    if deliver:
        handoff_event(
            event,
            delivery_script=delivery_script,
            session_mode=session_mode,
            dry_run=dry_run,
            queue_dir=queue_dir,
            stdout_log=stdout_log,
        )


def release_one_pending_event(
    *,
    pending_release_events: dict[str, dict[str, object]],
    pending_release_order: list[str],
    log_file: str,
    deliver: bool,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
    queue_dir: str,
    stdout_log: str,
    last_report_signature: dict[str, str],
) -> bool:
    while pending_release_order:
        target = pending_release_order.pop(0)
        event = pending_release_events.pop(target, None)
        if event is None:
            continue
        release_event(
            event,
            target=target,
            log_file=log_file,
            deliver=deliver,
            delivery_script=delivery_script,
            session_mode=session_mode,
            dry_run=dry_run,
            queue_dir=queue_dir,
            stdout_log=stdout_log,
            last_report_signature=last_report_signature,
        )
        return True
    return False


def main() -> int:
    args = parse_args()
    watched_targets = normalize_targets(args)
    if not watched_targets:
        raise SystemExit("at least one --target is required")
    bound_codex_thread_id = read_tmux_session_binding()
    if args.deliver and not bound_codex_thread_id:
        raise SystemExit("CODEX_THREAD_ID is not bound; refusing to deliver watcher events")

    capture_lines = capture_line_count_from_start(args.start)
    last_report_signature: dict[str, str] = {}
    cached_snapshots: dict[str, dict[str, object]] = {}
    last_output_hash: dict[str, str] = {}
    unchanged_output_count: dict[str, int] = {}
    pending_release_events: dict[str, dict[str, object]] = {}
    pending_release_order: list[str] = []

    while True:
        unavailable_targets = 0
        detached_targets = 0
        for target in watched_targets:
            current_event: dict[str, object] | None = None
            try:
                snapshot = capture_snapshot(target, args.start)
                cached_snapshots[target] = snapshot
            except (subprocess.CalledProcessError, RuntimeError):
                unavailable_targets += 1
                reset_output_hash_state(
                    target,
                    last_output_hash=last_output_hash,
                    unchanged_output_count=unchanged_output_count,
                )
                current_event = build_unreachable_event(
                    target,
                    reason="pane 不可达",
                    codex_thread_id=bound_codex_thread_id,
                    cached_snapshot=cached_snapshots.get(target),
                )
            else:
                classification = classify_snapshot(snapshot)
                if classification is None:
                    unchanged_count = advance_output_hash_state(
                        target,
                        snapshot,
                        last_output_hash=last_output_hash,
                        unchanged_output_count=unchanged_output_count,
                    )
                    if unchanged_count < DEFAULT_UNCHANGED_OUTPUT_THRESHOLD:
                        last_report_signature.pop(target, None)
                        clear_pending_event(
                            target,
                            pending_release_events=pending_release_events,
                            pending_release_order=pending_release_order,
                        )
                        continue
                    current_event = build_hash_stopped_event(
                        snapshot,
                        codex_thread_id=bound_codex_thread_id,
                        unchanged_count=unchanged_count,
                        interval_seconds=args.interval,
                        capture_lines=capture_lines,
                    )
                else:
                    event_name, state_label, state = classification
                    extra_fields: dict[str, object] | None = None
                    if event_name == "session_detached":
                        detached_targets += 1
                        reset_output_hash_state(
                            target,
                            last_output_hash=last_output_hash,
                            unchanged_output_count=unchanged_output_count,
                        )
                    elif event_name == "pane_stopped":
                        reset_output_hash_state(
                            target,
                            last_output_hash=last_output_hash,
                            unchanged_output_count=unchanged_output_count,
                        )
                        extra_fields = {"stop_reason": "pane_dead"}
                    current_event = build_state_event(
                        snapshot,
                        event_name=event_name,
                        state_label=state_label,
                        state=state,
                        reachable=True,
                        codex_thread_id=bound_codex_thread_id,
                        extra_fields=extra_fields,
                    )

            if current_event is None:
                clear_pending_event(
                    target,
                    pending_release_events=pending_release_events,
                    pending_release_order=pending_release_order,
                )
                continue

            queue_pending_event(
                target,
                current_event,
                pending_release_events=pending_release_events,
                pending_release_order=pending_release_order,
                last_report_signature=last_report_signature,
            )

        downstream_idle = (not args.deliver) or delivery_queue_is_idle(args.delivery_queue_dir)
        if downstream_idle:
            release_one_pending_event(
                pending_release_events=pending_release_events,
                pending_release_order=pending_release_order,
                log_file=args.log_file,
                deliver=args.deliver,
                delivery_script=args.delivery_script,
                session_mode=args.session_mode,
                dry_run=args.deliver_dry_run,
                queue_dir=args.delivery_queue_dir,
                stdout_log=args.delivery_stdout_log,
                last_report_signature=last_report_signature,
            )

        if detached_targets >= len(watched_targets):
            if pending_release_events or not downstream_idle:
                if args.once:
                    return 0
                time.sleep(args.interval)
                continue
            clear_runtime_ledger()
            sys.stderr.write("formal session is detached; watcher exiting\n")
            return 0
        if unavailable_targets >= len(watched_targets):
            if pending_release_events or not downstream_idle:
                if args.once:
                    return 0
                time.sleep(args.interval)
                continue
            clear_runtime_ledger()
            sys.stderr.write("all watched targets are unavailable; watcher exiting\n")
            return 0
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
