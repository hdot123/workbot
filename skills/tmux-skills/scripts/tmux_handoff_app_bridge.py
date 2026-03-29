#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import select
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build_tmux_handoff_bundle import build_bundle


DEFAULT_QUEUE_DIR = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/delivery-queue")
DEFAULT_RECEIPTS_LOG = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/app-thread-delivery-receipts.jsonl")
DEFAULT_STDOUT_LOG = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/tmux-handoff-app-bridge.stdout.log")
DEFAULT_PID_FILE = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/tmux-handoff-app-bridge.pid")
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_CONFIRM_TIMEOUT_SECONDS = 15.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RETRIES = 1


class AppServerError(RuntimeError):
    pass


@dataclass
class DeliveryReceipt:
    event_id: str
    status: str
    thread_id: str
    message: str
    turn_id: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "recorded_at": time.time(),
            "event_id": self.event_id,
            "status": self.status,
            "thread_id": self.thread_id,
            "message": self.message,
        }
        if self.turn_id:
            payload["turn_id"] = self.turn_id
        if self.reason:
            payload["reason"] = self.reason
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Long-running bridge that delivers tmux handoff queue events into Codex app threads via app-server."
    )
    parser.add_argument("--queue-dir", default=str(DEFAULT_QUEUE_DIR), help="Directory containing queued event files.")
    parser.add_argument("--receipts-log", default=str(DEFAULT_RECEIPTS_LOG), help="JSONL file recording delivery receipts.")
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="PID file used for singleton bridge ownership.")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS, help="Queue polling interval.")
    parser.add_argument("--confirm-timeout", type=float, default=DEFAULT_CONFIRM_TIMEOUT_SECONDS, help="Receipt confirmation timeout after turn/start.")
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT_SECONDS, help="App-server request timeout.")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Retries per queue item before moving on to the next polling cycle.")
    parser.add_argument("--once", action="store_true", help="Process the queue once and exit.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if "tmux_skills_handoff" in payload:
        return payload
    return build_bundle(payload, table="tmux_notifications_raw", session_mode="fixed")


def target_thread_id(bundle: dict[str, Any]) -> str:
    tmux_handoff = bundle.get("tmux_skills_handoff", {})
    target = tmux_handoff.get("target", {})
    payload = tmux_handoff.get("payload", {})
    for candidate in (target.get("thread_id"), payload.get("codex_thread_id")):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def bundle_message(bundle: dict[str, Any]) -> str:
    notification = bundle.get("tmux_skills_handoff", {}).get("notification", {})
    return str(notification.get("message") or "").strip()


def bundle_deliverable(bundle: dict[str, Any]) -> bool:
    notification = bundle.get("tmux_skills_handoff", {}).get("notification", {})
    return bool(notification.get("deliverable"))


def append_receipt(path: Path, receipt: DeliveryReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        json.dump(receipt.as_dict(), handle, ensure_ascii=False)
        handle.write("\n")


def load_receipts(path: Path) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return receipts
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        event_id = str(entry.get("event_id") or "").strip()
        if not event_id:
            continue
        receipts[event_id] = entry
    return receipts


def maybe_ack_queue_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def normalize_message_text(content_items: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for item in content_items:
        if item.get("type") == "text":
            chunks.append(str(item.get("text") or ""))
    return "".join(chunks).strip()


def turn_contains_user_message(thread: dict[str, Any], turn_id: str, message: str) -> bool:
    normalized_message = message.strip()
    for turn in thread.get("turns", []):
        if str(turn.get("id") or "").strip() != turn_id:
            continue
        for item in turn.get("items", []):
            if item.get("type") != "userMessage":
                continue
            content_items = item.get("content") or []
            if normalize_message_text(content_items) == normalized_message:
                return True
    return False


def acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise SystemExit(0)
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


class AppServerClient:
    def __init__(self, *, request_timeout: float) -> None:
        self.request_timeout = request_timeout
        self.process: subprocess.Popen[str] | None = None
        self.next_request_id = 1
        self.notifications: list[dict[str, Any]] = []

    def ensure_started(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            self.process = subprocess.Popen(
                ["codex", "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise AppServerError(str(exc) or "failed to start codex app-server") from exc
        self.notifications.clear()
        self.request(
            "initialize",
            {
                "clientInfo": {"name": "tmux-handoff-app-bridge", "version": "0.1"},
                "capabilities": None,
            },
        )

    def close(self) -> None:
        if not self.process:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def request(self, method: str, params: dict[str, Any] | None) -> dict[str, Any]:
        self.ensure_started()
        assert self.process is not None
        assert self.process.stdin is not None

        request_id = self.next_request_id
        self.next_request_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

        deadline = time.monotonic() + self.request_timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AppServerError(
                    f"codex app-server exited with code {self.process.returncode}"
                )
            message = self._read_message(max(0.1, deadline - time.monotonic()))
            if message is None:
                continue
            if "id" in message:
                if message["id"] != request_id:
                    continue
                if "error" in message:
                    raise AppServerError(json.dumps(message["error"], ensure_ascii=False))
                return dict(message.get("result") or {})
            self.notifications.append(message)
        raise AppServerError(f"timeout waiting for app-server response to {method}")

    def wait_for_delivery_receipt(self, *, thread_id: str, turn_id: str, message: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        saw_turn_started = False
        while time.monotonic() < deadline:
            buffered: list[dict[str, Any]] = []
            while self.notifications:
                buffered.append(self.notifications.pop(0))
            for notification in buffered:
                if self._is_turn_started(notification, thread_id, turn_id):
                    saw_turn_started = True
                if saw_turn_started and self._is_user_message_receipt(notification, thread_id, turn_id, message):
                    return True

            thread = self.request(
                "thread/read",
                {
                    "threadId": thread_id,
                    "includeTurns": True,
                },
            ).get("thread", {})
            if turn_contains_user_message(thread, turn_id, message):
                return True
        return False

    def _read_message(self, timeout: float) -> dict[str, Any] | None:
        assert self.process is not None
        assert self.process.stdout is not None
        assert self.process.stderr is not None

        readable, _, _ = select.select([self.process.stdout, self.process.stderr], [], [], timeout)
        if not readable:
            return None
        for stream in readable:
            line = stream.readline()
            if not line:
                continue
            line = line.rstrip("\n")
            if stream is self.process.stderr:
                print(line, file=sys.stderr)
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError as exc:
                raise AppServerError(f"invalid JSON from app-server: {exc}") from exc
        return None

    @staticmethod
    def _is_turn_started(notification: dict[str, Any], thread_id: str, turn_id: str) -> bool:
        params = notification.get("params") or {}
        turn = params.get("turn") or {}
        return (
            notification.get("method") == "turn/started"
            and str(params.get("threadId") or "").strip() == thread_id
            and str(turn.get("id") or "").strip() == turn_id
        )

    @staticmethod
    def _is_user_message_receipt(notification: dict[str, Any], thread_id: str, turn_id: str, message: str) -> bool:
        if notification.get("method") not in {"item/started", "item/completed"}:
            return False
        params = notification.get("params") or {}
        item = params.get("item") or {}
        if str(params.get("threadId") or "").strip() != thread_id:
            return False
        if str(params.get("turnId") or "").strip() != turn_id:
            return False
        if item.get("type") != "userMessage":
            return False
        return normalize_message_text(item.get("content") or []) == message.strip()


def process_queue_item(
    path: Path,
    *,
    client: AppServerClient,
    receipts_log: Path,
    receipts_by_event_id: dict[str, dict[str, Any]],
    confirm_timeout: float,
    max_retries: int,
) -> None:
    payload = load_json(path)
    bundle = ensure_bundle(payload)
    tmux_handoff = bundle.get("tmux_skills_handoff", {})
    event_id = str(bundle.get("event_id") or tmux_handoff.get("event_id") or "").strip()
    message = bundle_message(bundle)
    thread_id = target_thread_id(bundle)

    if not event_id:
        raise AppServerError(f"event file missing event_id: {path}")
    if not message:
        raise AppServerError(f"event file missing notification message: {path}")
    if not thread_id:
        raise AppServerError(f"event file missing target thread id: {path}")

    latest_receipt = receipts_by_event_id.get(event_id)
    if latest_receipt and latest_receipt.get("status") in {"delivered", "skipped"}:
        maybe_ack_queue_file(path)
        return

    if not bundle_deliverable(bundle):
        append_receipt(receipts_log, DeliveryReceipt(event_id, "skipped", thread_id, message, reason="non_deliverable_event"))
        receipts_by_event_id[event_id] = {"status": "skipped", "thread_id": thread_id, "message": message}
        maybe_ack_queue_file(path)
        return

    if latest_receipt and latest_receipt.get("status") == "turn_started":
        turn_id = str(latest_receipt.get("turn_id") or "").strip()
        if turn_id and client.wait_for_delivery_receipt(thread_id=thread_id, turn_id=turn_id, message=message, timeout=confirm_timeout):
            append_receipt(receipts_log, DeliveryReceipt(event_id, "delivered", thread_id, message, turn_id=turn_id))
            receipts_by_event_id[event_id] = {"status": "delivered", "thread_id": thread_id, "turn_id": turn_id, "message": message}
            maybe_ack_queue_file(path)
        return

    for _ in range(max(1, max_retries)):
        try:
            resumed = client.request(
                "thread/resume",
                {
                    "threadId": thread_id,
                    "persistExtendedHistory": False,
                },
            )
        except AppServerError as exc:
            append_receipt(receipts_log, DeliveryReceipt(event_id, "thread_resume_failed", thread_id, message, reason=str(exc)))
            receipts_by_event_id[event_id] = {"status": "thread_resume_failed", "thread_id": thread_id, "message": message, "reason": str(exc)}
            return

        thread = resumed.get("thread", {})
        status = thread.get("status") or {}
        if str(status.get("type") or "").strip() not in {"", "idle"}:
            reason = f"thread_not_idle:{json.dumps(status, ensure_ascii=False)}"
            append_receipt(receipts_log, DeliveryReceipt(event_id, "thread_not_idle", thread_id, message, reason=reason))
            receipts_by_event_id[event_id] = {"status": "thread_not_idle", "thread_id": thread_id, "message": message, "reason": reason}
            return

        try:
            turn = client.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": message, "text_elements": []}],
                },
            ).get("turn", {})
        except AppServerError as exc:
            append_receipt(receipts_log, DeliveryReceipt(event_id, "turn_start_failed", thread_id, message, reason=str(exc)))
            receipts_by_event_id[event_id] = {"status": "turn_start_failed", "thread_id": thread_id, "message": message, "reason": str(exc)}
            return

        turn_id = str(turn.get("id") or "").strip()
        if not turn_id:
            append_receipt(receipts_log, DeliveryReceipt(event_id, "turn_start_failed", thread_id, message, reason="missing_turn_id"))
            receipts_by_event_id[event_id] = {"status": "turn_start_failed", "thread_id": thread_id, "message": message, "reason": "missing_turn_id"}
            return

        append_receipt(receipts_log, DeliveryReceipt(event_id, "turn_started", thread_id, message, turn_id=turn_id))
        receipts_by_event_id[event_id] = {"status": "turn_started", "thread_id": thread_id, "turn_id": turn_id, "message": message}
        if client.wait_for_delivery_receipt(thread_id=thread_id, turn_id=turn_id, message=message, timeout=confirm_timeout):
            append_receipt(receipts_log, DeliveryReceipt(event_id, "delivered", thread_id, message, turn_id=turn_id))
            receipts_by_event_id[event_id] = {"status": "delivered", "thread_id": thread_id, "turn_id": turn_id, "message": message}
            maybe_ack_queue_file(path)
        return


def main() -> int:
    args = parse_args()
    queue_dir = Path(args.queue_dir)
    receipts_log = Path(args.receipts_log)
    _lock_handle = acquire_lock(Path(args.pid_file))
    client = AppServerClient(request_timeout=args.request_timeout)
    receipts_by_event_id = load_receipts(receipts_log)
    queue_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            queue_files = sorted(path for path in queue_dir.glob("*.json") if path.is_file())
            for path in queue_files:
                try:
                    process_queue_item(
                        path,
                        client=client,
                        receipts_log=receipts_log,
                        receipts_by_event_id=receipts_by_event_id,
                        confirm_timeout=args.confirm_timeout,
                        max_retries=args.max_retries,
                    )
                except Exception as exc:
                    print(f"bridge failed to process {path}: {exc}", file=sys.stderr)
            if args.once:
                return 0
            time.sleep(max(0.1, args.poll_interval))
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
