#!/usr/bin/env python3
from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("tmux_handoff_app_bridge.py")
# ==============================================================================

import argparse
import fcntl
import json
import os
import select
import socket
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from build_tmux_handoff_bundle import build_bundle


DEFAULT_QUEUE_DIR = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/delivery-queue")
DEFAULT_RECEIPTS_LOG = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/window-ipc-delivery-receipts.jsonl"
)
DEFAULT_STDOUT_LOG = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/tmux-handoff-window-ipc-bridge.stdout.log"
)
DEFAULT_PID_FILE = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/tmux-handoff-window-ipc-bridge.pid"
)
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_CONFIRM_TIMEOUT_SECONDS = 5.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_IDLE_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_RETRIES = 1
MAX_IPC_FRAME_BYTES = 256 * 1024 * 1024
IPC_METHOD_VERSIONS = {
    "initialize": 0,
    "thread-follower-start-turn": 1,
    "thread-stream-state-changed": 5,
    "client-status-changed": 0,
}
INITIALIZING_CLIENT_ID = "initializing-client"


class WindowIpcError(RuntimeError):
    pass


@dataclass
class DeliveryReceipt:
    event_id: str
    status: str
    thread_id: str
    message: str
    turn_id: str | None = None
    handled_by_client_id: str | None = None
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
        if self.handled_by_client_id:
            payload["handled_by_client_id"] = self.handled_by_client_id
        if self.reason:
            payload["reason"] = self.reason
        return payload


@dataclass
class WindowIpcDeliveryResult:
    handled_by_client_id: str
    turn_id: str | None
    visibility_broadcast_observed: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Long-running bridge that delivers tmux handoff queue events into the current Codex window via local window IPC."
    )
    parser.add_argument("--queue-dir", default=str(DEFAULT_QUEUE_DIR), help="Directory containing queued event files.")
    parser.add_argument("--receipts-log", default=str(DEFAULT_RECEIPTS_LOG), help="JSONL file recording delivery receipts.")
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE), help="PID file used for singleton bridge ownership.")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS, help="Queue polling interval.")
    parser.add_argument(
        "--confirm-timeout",
        type=float,
        default=DEFAULT_CONFIRM_TIMEOUT_SECONDS,
        help="Optional wait after owner-window turn start to observe a stream-state broadcast from that same window.",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=DEFAULT_IDLE_TIMEOUT_SECONDS,
        help="Maximum wait per polling cycle for the target thread to return to idle before allowing the next queued delivery.",
    )
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT_SECONDS, help="Window IPC request timeout.")
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


def ipc_method_version(method: str) -> int:
    return IPC_METHOD_VERSIONS.get(method, 0)


def default_ipc_socket_path() -> Path:
    configured = os.environ.get("CODEX_IPC_SOCKET", "").strip()
    if configured:
        return Path(configured)
    temp_root = Path(tempfile.gettempdir()) / "codex-ipc"
    uid = os.getuid() if hasattr(os, "getuid") else None
    if uid is None:
        return temp_root / "ipc.sock"
    return temp_root / f"ipc-{uid}.sock"


def encode_ipc_message(message: dict[str, Any]) -> bytes:
    encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
    size = len(encoded)
    if size > MAX_IPC_FRAME_BYTES:
        raise WindowIpcError(f"IPC frame too large: {size} bytes")
    return size.to_bytes(4, byteorder="little", signed=False) + encoded


def extract_turn_id(response: dict[str, Any]) -> str | None:
    candidates = [
        response.get("result"),
        (response.get("result") or {}).get("result"),
        (response.get("result") or {}).get("turn"),
        ((response.get("result") or {}).get("result") or {}).get("turn"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            turn = candidate.get("turn") if "turn" in candidate else candidate
            if isinstance(turn, dict):
                turn_id = str(turn.get("id") or "").strip()
                if turn_id:
                    return turn_id
    return None


class CodexWindowIpcClient:
    def __init__(self, *, request_timeout: float, client_type: str = "tmux-handoff-app-bridge") -> None:
        self.request_timeout = request_timeout
        self.client_type = client_type
        self.socket: socket.socket | None = None
        self.client_id = INITIALIZING_CLIENT_ID
        self._buffer = bytearray()
        self._backlog: list[dict[str, Any]] = []

    def close(self) -> None:
        if self.socket is None:
            return
        try:
            self.socket.close()
        finally:
            self.socket = None
            self.client_id = INITIALIZING_CLIENT_ID
            self._buffer.clear()
            self._backlog.clear()

    def ensure_connected(self) -> None:
        if self.socket is not None:
            return
        socket_path = default_ipc_socket_path()
        if not socket_path.exists():
            raise WindowIpcError(f"Codex window IPC socket not found: {socket_path}")
        if os.name == "nt":
            raise WindowIpcError("Windows named-pipe Codex IPC is not supported by tmux-skills")
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.connect(str(socket_path))
        except OSError as exc:
            connection.close()
            raise WindowIpcError(str(exc) or f"failed to connect to Codex IPC socket {socket_path}") from exc
        self.socket = connection
        response = self._send_request_raw("initialize", {"clientType": self.client_type})
        if response.get("resultType") != "success":
            self.close()
            raise WindowIpcError(self._response_error(response) or "Codex IPC initialize failed")
        client_id = str((response.get("result") or {}).get("clientId") or "").strip()
        if not client_id:
            self.close()
            raise WindowIpcError("Codex IPC initialize succeeded without a clientId")
        self.client_id = client_id

    def deliver_turn_to_current_window(
        self,
        *,
        thread_id: str,
        message: str,
        confirm_timeout: float,
    ) -> WindowIpcDeliveryResult:
        response = self.send_request(
            "thread-follower-start-turn",
            {
                "conversationId": thread_id,
                "turnStartParams": {
                    "input": [{"type": "text", "text": message, "text_elements": []}],
                    "attachments": [],
                },
            },
        )
        if response.get("resultType") != "success":
            raise WindowIpcError(self._response_error(response) or "thread-follower-start-turn failed")
        handled_by_client_id = str(response.get("handledByClientId") or "").strip()
        if not handled_by_client_id:
            raise WindowIpcError("thread-follower-start-turn succeeded without handledByClientId")
        turn_id = extract_turn_id(response)
        visibility_broadcast_observed = self.wait_for_stream_state_change(
            thread_id=thread_id,
            handled_by_client_id=handled_by_client_id,
            timeout=confirm_timeout,
        )
        return WindowIpcDeliveryResult(
            handled_by_client_id=handled_by_client_id,
            turn_id=turn_id,
            visibility_broadcast_observed=visibility_broadcast_observed,
        )

    def send_request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        target_client_id: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_connected()
        return self._send_request_raw(method, params, target_client_id=target_client_id)

    def wait_for_stream_state_change(
        self,
        *,
        thread_id: str,
        handled_by_client_id: str,
        timeout: float,
    ) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        deferred: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            message = self._next_message(deadline - time.monotonic())
            if message is None:
                continue
            if self._is_matching_stream_state_change(
                message,
                thread_id=thread_id,
                handled_by_client_id=handled_by_client_id,
            ):
                if deferred:
                    self._backlog = deferred + self._backlog
                return True
            deferred.append(message)
        if deferred:
            self._backlog = deferred + self._backlog
        return False

    def wait_for_thread_idle(
        self,
        *,
        thread_id: str,
        handled_by_client_id: str,
        timeout: float,
    ) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        deferred: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            message = self._next_message(deadline - time.monotonic())
            if message is None:
                continue
            if self._is_matching_idle_state_change(
                message,
                thread_id=thread_id,
                handled_by_client_id=handled_by_client_id,
            ):
                if deferred:
                    self._backlog = deferred + self._backlog
                return True
            deferred.append(message)
        if deferred:
            self._backlog = deferred + self._backlog
        return False

    def _send_request_raw(
        self,
        method: str,
        params: dict[str, Any],
        *,
        target_client_id: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid4())
        request = {
            "type": "request",
            "requestId": request_id,
            "sourceClientId": self.client_id,
            "version": ipc_method_version(method),
            "method": method,
            "params": params,
        }
        if target_client_id:
            request["targetClientId"] = target_client_id
        self._write_message(request)
        deadline = time.monotonic() + self.request_timeout
        deferred: list[dict[str, Any]] = []
        while time.monotonic() < deadline:
            message = self._next_message(deadline - time.monotonic())
            if message is None:
                continue
            if message.get("type") == "response" and str(message.get("requestId") or "") == request_id:
                if deferred:
                    self._backlog = deferred + self._backlog
                return message
            deferred.append(message)
        if deferred:
            self._backlog = deferred + self._backlog
        raise WindowIpcError(f"timeout waiting for Codex window IPC response to {method}")

    def _next_message(self, timeout: float) -> dict[str, Any] | None:
        if self._backlog:
            return self._backlog.pop(0)
        assert self.socket is not None
        remaining = max(0.0, timeout)
        readable, _, _ = select.select([self.socket], [], [], remaining)
        if not readable:
            return None
        chunk = self.socket.recv(64 * 1024)
        if not chunk:
            self.close()
            raise WindowIpcError("Codex window IPC connection closed")
        self._buffer.extend(chunk)
        frames = self._drain_frames()
        if not frames:
            return None
        self._backlog.extend(frames[1:])
        return frames[0]

    def _drain_frames(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        while True:
            if len(self._buffer) < 4:
                return messages
            frame_size = int.from_bytes(self._buffer[:4], byteorder="little", signed=False)
            if frame_size > MAX_IPC_FRAME_BYTES:
                raise WindowIpcError(f"IPC frame exceeded limit ({frame_size} bytes)")
            if len(self._buffer) < 4 + frame_size:
                return messages
            frame = bytes(self._buffer[4 : 4 + frame_size])
            del self._buffer[: 4 + frame_size]
            try:
                messages.append(json.loads(frame.decode("utf-8")))
            except json.JSONDecodeError as exc:
                raise WindowIpcError(f"invalid JSON from Codex window IPC: {exc}") from exc

    def _write_message(self, message: dict[str, Any]) -> None:
        assert self.socket is not None
        payload = encode_ipc_message(message)
        try:
            self.socket.sendall(payload)
        except OSError as exc:
            self.close()
            raise WindowIpcError(str(exc) or "failed to write to Codex window IPC") from exc

    @staticmethod
    def _is_matching_stream_state_change(
        message: dict[str, Any],
        *,
        thread_id: str,
        handled_by_client_id: str,
    ) -> bool:
        if message.get("type") != "broadcast":
            return False
        if message.get("method") != "thread-stream-state-changed":
            return False
        params = message.get("params") or {}
        return (
            str(params.get("conversationId") or "").strip() == thread_id
            and str(message.get("sourceClientId") or "").strip() == handled_by_client_id
        )

    @classmethod
    def _is_matching_idle_state_change(
        cls,
        message: dict[str, Any],
        *,
        thread_id: str,
        handled_by_client_id: str,
    ) -> bool:
        if not cls._is_matching_stream_state_change(
            message,
            thread_id=thread_id,
            handled_by_client_id=handled_by_client_id,
        ):
            return False
        params = message.get("params") or {}
        change = params.get("change") or {}
        runtime_state = change.get("threadRuntimeStatus")
        if not isinstance(runtime_state, dict):
            runtime_state = ((change.get("conversationState") or {}).get("threadRuntimeStatus"))
        return str((runtime_state or {}).get("type") or "").strip() == "idle"

    @staticmethod
    def _response_error(response: dict[str, Any]) -> str:
        error = response.get("error")
        if isinstance(error, str) and error:
            return error
        return json.dumps(error, ensure_ascii=False) if error is not None else ""


def process_queue_item(
    path: Path,
    *,
    client: CodexWindowIpcClient,
    receipts_log: Path,
    receipts_by_event_id: dict[str, dict[str, Any]],
    confirm_timeout: float,
    idle_timeout: float,
    max_retries: int,
) -> None:
    payload = load_json(path)
    bundle = ensure_bundle(payload)
    tmux_handoff = bundle.get("tmux_skills_handoff", {})
    event_id = str(bundle.get("event_id") or tmux_handoff.get("event_id") or "").strip()
    message = bundle_message(bundle)
    thread_id = target_thread_id(bundle)

    if not event_id:
        raise WindowIpcError(f"event file missing event_id: {path}")
    if not message:
        raise WindowIpcError(f"event file missing notification message: {path}")
    if not thread_id:
        raise WindowIpcError(f"event file missing target thread id: {path}")

    latest_receipt = receipts_by_event_id.get(event_id)
    if latest_receipt and latest_receipt.get("status") in {"delivered", "skipped"}:
        maybe_ack_queue_file(path)
        return

    if latest_receipt and latest_receipt.get("status") == "accepted_waiting_idle":
        handled_by_client_id = str(latest_receipt.get("handled_by_client_id") or "").strip()
        if not handled_by_client_id:
            raise WindowIpcError(f"receipt missing handled_by_client_id while waiting for idle: {event_id}")
        idle_observed = client.wait_for_thread_idle(
            thread_id=thread_id,
            handled_by_client_id=handled_by_client_id,
            timeout=idle_timeout,
        )
        if not idle_observed:
            return
        append_receipt(
            receipts_log,
            DeliveryReceipt(
                event_id,
                "delivered",
                thread_id,
                message,
                turn_id=str(latest_receipt.get("turn_id") or "").strip() or None,
                handled_by_client_id=handled_by_client_id,
                reason="owner_window_response+thread_stream_state_changed+thread_idle",
            ),
        )
        receipts_by_event_id[event_id] = {
            "status": "delivered",
            "thread_id": thread_id,
            "message": message,
            "turn_id": str(latest_receipt.get("turn_id") or "").strip() or None,
            "handled_by_client_id": handled_by_client_id,
            "reason": "owner_window_response+thread_stream_state_changed+thread_idle",
        }
        maybe_ack_queue_file(path)
        return

    if not bundle_deliverable(bundle):
        append_receipt(
            receipts_log,
            DeliveryReceipt(event_id, "skipped", thread_id, message, reason="non_deliverable_event"),
        )
        receipts_by_event_id[event_id] = {"status": "skipped", "thread_id": thread_id, "message": message}
        maybe_ack_queue_file(path)
        return

    for _ in range(max(1, max_retries)):
        try:
            result = client.deliver_turn_to_current_window(
                thread_id=thread_id,
                message=message,
                confirm_timeout=confirm_timeout,
            )
        except WindowIpcError as exc:
            reason = str(exc) or "window_ipc_delivery_failed"
            status = "window_ipc_connect_failed" if "socket" in reason or "connect" in reason else "window_ipc_request_failed"
            append_receipt(
                receipts_log,
                DeliveryReceipt(event_id, status, thread_id, message, reason=reason),
            )
            receipts_by_event_id[event_id] = {
                "status": status,
                "thread_id": thread_id,
                "message": message,
                "reason": reason,
            }
            return

        confirmation_reason = "owner_window_response"
        if result.visibility_broadcast_observed:
            confirmation_reason = "owner_window_response+thread_stream_state_changed"
        idle_observed = client.wait_for_thread_idle(
            thread_id=thread_id,
            handled_by_client_id=result.handled_by_client_id,
            timeout=idle_timeout,
        )
        if not idle_observed:
            append_receipt(
                receipts_log,
                DeliveryReceipt(
                    event_id,
                    "accepted_waiting_idle",
                    thread_id,
                    message,
                    turn_id=result.turn_id,
                    handled_by_client_id=result.handled_by_client_id,
                    reason=confirmation_reason,
                ),
            )
            receipts_by_event_id[event_id] = {
                "status": "accepted_waiting_idle",
                "thread_id": thread_id,
                "message": message,
                "turn_id": result.turn_id,
                "handled_by_client_id": result.handled_by_client_id,
                "reason": confirmation_reason,
            }
            return
        append_receipt(
            receipts_log,
            DeliveryReceipt(
                event_id,
                "delivered",
                thread_id,
                message,
                turn_id=result.turn_id,
                handled_by_client_id=result.handled_by_client_id,
                reason=f"{confirmation_reason}+thread_idle",
            ),
        )
        receipts_by_event_id[event_id] = {
            "status": "delivered",
            "thread_id": thread_id,
            "message": message,
            "turn_id": result.turn_id,
            "handled_by_client_id": result.handled_by_client_id,
            "reason": f"{confirmation_reason}+thread_idle",
        }
        maybe_ack_queue_file(path)
        return


def main() -> int:
    args = parse_args()
    queue_dir = Path(args.queue_dir)
    receipts_log = Path(args.receipts_log)
    _lock_handle = acquire_lock(Path(args.pid_file))
    client = CodexWindowIpcClient(request_timeout=args.request_timeout)
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
                        idle_timeout=args.idle_timeout,
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
