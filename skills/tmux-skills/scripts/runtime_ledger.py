#!/usr/bin/env python3
"""Helpers for the canonical tmux-skills runtime ledger."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


RUNTIME_ARTIFACT_DIR = Path("/Users/busiji/workbot/workspace/artifacts/tmux-runtime")
CURRENT_RUNTIME_LEDGER_PATH = RUNTIME_ARTIFACT_DIR / "current-runtime.json"

DEFAULT_FORMAL_SESSION_NAME = "formal-session"
DEFAULT_FORMAL_PANE_COUNT = 4
DEFAULT_WORKER_CEILING = 3
WHITE_ROLE_TITLES = ("dev-bot", "qa-bot", "doc-bot")
DEFAULT_FORMAL_PANE_TITLES = (
    "dev-bot",
    "dev-bot",
    "qa-bot",
    "doc-bot",
)


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_runtime_artifact_dir() -> None:
    RUNTIME_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def load_current_runtime_ledger() -> dict[str, Any]:
    if not CURRENT_RUNTIME_LEDGER_PATH.exists():
        return {}
    return json.loads(CURRENT_RUNTIME_LEDGER_PATH.read_text(encoding="utf-8"))


def write_current_runtime_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime_artifact_dir()
    CURRENT_RUNTIME_LEDGER_PATH.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ledger


def normalize_target(value: Any | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_role(value: Any | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_valid_target(value: str) -> bool:
    if ":" not in value:
        return False
    _, _, pane_ref = value.partition(":")
    if "." not in pane_ref:
        return False
    window_index, _, pane_index = pane_ref.partition(".")
    return bool(window_index.strip() and pane_index.strip())


def build_slot_bindings_from_targets(targets: list[str], pane_titles: list[str]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    monitor_assigned = False
    for index, (target, role) in enumerate(zip(targets, pane_titles), start=1):
        slot_name = f"pane_{index}"
        if role == "qa-bot" and not monitor_assigned:
            slot_name = "monitor"
            monitor_assigned = True
        bindings[slot_name] = {"role": role, "target": target}
    return bindings


def parse_slot_binding_entry(entry: str) -> tuple[str, dict[str, str]]:
    if "=" not in entry:
        raise ValueError("slot binding must be in the form slot=role@target")
    slot_name, _, raw_value = entry.partition("=")
    normalized_slot = slot_name.strip()
    if not normalized_slot:
        raise ValueError("slot name cannot be empty")
    role_text, separator, target_text = raw_value.partition("@")
    role = normalize_role(role_text)
    target = normalize_target(target_text if separator else "")
    if not role:
        raise ValueError("slot binding role cannot be empty")
    if target and not is_valid_target(target):
        raise ValueError(f"slot binding target is invalid: {target}")
    return normalized_slot, {"role": role, "target": target}


def _normalize_slot_binding(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        role = normalize_role(value.get("role"))
        target = normalize_target(value.get("target"))
    else:
        role = normalize_role(value)
        target = ""
    if not role:
        return {}
    return {"role": role, "target": target}


def coerce_slot_bindings(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    bindings: dict[str, dict[str, str]] = {}
    for slot_name, raw_binding in value.items():
        normalized_slot = str(slot_name).strip()
        if not normalized_slot:
            continue
        normalized_binding = _normalize_slot_binding(raw_binding)
        if not normalized_binding:
            continue
        bindings[normalized_slot] = normalized_binding
    return bindings


def coerce_watcher(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    targets = value.get("targets")
    normalized_targets = []
    if isinstance(targets, list):
        normalized_targets = sorted(
            {
                normalize_target(item)
                for item in targets
                if normalize_target(item) and is_valid_target(normalize_target(item))
            }
        )
    watcher: dict[str, Any] = {
        "armed": bool(value.get("armed")),
        "targets": normalized_targets,
    }
    if value.get("pid") is not None:
        watcher["pid"] = value.get("pid")
    if value.get("transport"):
        watcher["transport"] = str(value.get("transport")).strip()
    return watcher


def init_current_runtime_ledger(
    task_id: str,
    *,
    pane_count: int | None = None,
    topology_fingerprint: str = "",
    formal_session_name: str = DEFAULT_FORMAL_SESSION_NAME,
    slot_bindings: dict[str, dict[str, str]] | None = None,
    watcher: dict[str, Any] | None = None,
    codex_thread_bound: bool = False,
    runtime_status: str = "INIT_IN_PROGRESS",
    worker_ceiling: int = DEFAULT_WORKER_CEILING,
) -> dict[str, Any]:
    now = utc_now()
    ledger = {
        "task_id": task_id,
        "runtime_status": runtime_status,
        "formal_session_name": normalize_target(formal_session_name)
        or DEFAULT_FORMAL_SESSION_NAME,
        "pane_count": pane_count,
        "topology_fingerprint": str(topology_fingerprint or "").strip(),
        "slot_bindings": coerce_slot_bindings(slot_bindings or {}),
        "watcher": coerce_watcher(watcher or {}),
        "codex_thread_bound": bool(codex_thread_bound),
        "worker_ceiling": int(worker_ceiling),
        "created_at": now,
        "updated_at": now,
    }
    return write_current_runtime_ledger(ledger)


def update_current_runtime_ledger(**fields: Any) -> dict[str, Any]:
    ledger = load_current_runtime_ledger()
    if not ledger:
        raise FileNotFoundError(f"runtime ledger not found: {CURRENT_RUNTIME_LEDGER_PATH}")
    if "slot_bindings" in fields:
        fields["slot_bindings"] = coerce_slot_bindings(fields["slot_bindings"])
    if "watcher" in fields:
        fields["watcher"] = coerce_watcher(fields["watcher"])
    if "formal_session_name" in fields:
        fields["formal_session_name"] = (
            normalize_target(fields["formal_session_name"]) or DEFAULT_FORMAL_SESSION_NAME
        )
    if "topology_fingerprint" in fields:
        fields["topology_fingerprint"] = str(fields["topology_fingerprint"] or "").strip()
    if "codex_thread_bound" in fields:
        fields["codex_thread_bound"] = bool(fields["codex_thread_bound"])
    if "worker_ceiling" in fields:
        fields["worker_ceiling"] = int(fields["worker_ceiling"])
    ledger.update(fields)
    ledger["updated_at"] = utc_now()
    return write_current_runtime_ledger(ledger)


def merge_slot_bindings(
    base: dict[str, dict[str, str]],
    overrides: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    merged = dict(base)
    for slot_name, binding in overrides.items():
        merged[slot_name] = dict(binding)
    return merged


def apply_slot_binding_updates(
    updates: dict[str, dict[str, str]],
    *,
    allow_reassign: bool = False,
) -> dict[str, Any]:
    if not updates:
        return load_current_runtime_ledger()
    ledger = load_current_runtime_ledger()
    if not ledger:
        raise FileNotFoundError(f"runtime ledger not found: {CURRENT_RUNTIME_LEDGER_PATH}")
    current_bindings = coerce_slot_bindings(ledger.get("slot_bindings"))
    normalized_updates = coerce_slot_bindings(updates)
    for slot_name, binding in normalized_updates.items():
        current_binding = current_bindings.get(slot_name, {})
        current_target = normalize_target(current_binding.get("target"))
        next_target = normalize_target(binding.get("target"))
        if (
            not allow_reassign
            and current_target
            and next_target
            and current_target != next_target
        ):
            raise ValueError(
                "slot target reassignment is not allowed without allow_reassign=True: "
                f"{slot_name} is currently {current_target}, requested {next_target}"
            )
    merged = merge_slot_bindings(current_bindings, normalized_updates)
    return update_current_runtime_ledger(slot_bindings=merged)


def apply_slot_assignment_updates(
    updates: dict[str, str | None],
    *,
    allow_reassign: bool = False,
) -> dict[str, Any]:
    translated = {
        str(slot_name).strip(): {"role": normalize_role(role), "target": ""}
        for slot_name, role in (updates or {}).items()
        if str(slot_name).strip() and normalize_role(role)
    }
    return apply_slot_binding_updates(translated, allow_reassign=allow_reassign)


def evaluate_runtime_ledger_coherence(ledger: dict[str, Any]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []

    formal_session_name = normalize_target(ledger.get("formal_session_name"))
    if not formal_session_name:
        reasons.append("runtime ledger missing formal_session_name")

    topology_fingerprint = str(ledger.get("topology_fingerprint", "") or "").strip()
    if not topology_fingerprint:
        reasons.append("runtime ledger missing topology_fingerprint")

    raw_pane_count = ledger.get("pane_count")
    pane_count_value: int | None = None
    if raw_pane_count is None:
        reasons.append("runtime ledger missing pane_count")
    else:
        try:
            pane_count = int(raw_pane_count)
            pane_count_value = pane_count
        except (TypeError, ValueError):
            reasons.append("runtime ledger pane_count is invalid")
        else:
            if pane_count <= 0:
                reasons.append("runtime ledger pane_count must be a positive integer")

    raw_worker_ceiling = ledger.get("worker_ceiling")
    if raw_worker_ceiling is None:
        reasons.append("runtime ledger missing worker_ceiling")
    else:
        try:
            worker_ceiling = int(raw_worker_ceiling)
        except (TypeError, ValueError):
            reasons.append("runtime ledger worker_ceiling is invalid")
        else:
            if worker_ceiling != DEFAULT_WORKER_CEILING:
                reasons.append(
                    "runtime ledger worker_ceiling must match runtime default: "
                    f"expected={DEFAULT_WORKER_CEILING}, actual={worker_ceiling}"
                )

    if "codex_thread_bound" not in ledger:
        reasons.append("runtime ledger missing codex_thread_bound")
    elif not isinstance(ledger.get("codex_thread_bound"), bool):
        reasons.append("runtime ledger codex_thread_bound must be a boolean")

    watcher = coerce_watcher(ledger.get("watcher"))
    if not watcher:
        reasons.append("runtime ledger missing watcher")
    else:
        if "armed" not in watcher:
            reasons.append("runtime ledger watcher missing armed state")
        if not isinstance(watcher.get("armed"), bool):
            reasons.append("runtime ledger watcher.armed must be a boolean")
        watcher_targets = watcher.get("targets")
        if not isinstance(watcher_targets, list):
            reasons.append("runtime ledger watcher.targets must be a list")
        elif pane_count_value is not None and len(watcher_targets) != pane_count_value:
            reasons.append(
                "runtime ledger watcher.targets does not match pane_count: "
                f"expected={pane_count_value}, actual={len(watcher_targets)}"
            )

    slot_bindings = coerce_slot_bindings(ledger.get("slot_bindings"))
    if not slot_bindings:
        reasons.append("runtime ledger missing slot_bindings")
    else:
        if pane_count_value is not None and len(slot_bindings) != pane_count_value:
            reasons.append(
                "runtime ledger slot_bindings does not match pane_count: "
                f"expected={pane_count_value}, actual={len(slot_bindings)}"
            )
        for slot_name, binding in slot_bindings.items():
            role = normalize_role(binding.get("role"))
            target = normalize_target(binding.get("target"))
            if role not in WHITE_ROLE_TITLES:
                reasons.append(
                    f"runtime ledger slot_bindings.{slot_name}.role is invalid: {role or '<empty>'}"
                )
            if not target:
                reasons.append(f"runtime ledger slot_bindings.{slot_name}.target is missing")
            elif not is_valid_target(target):
                reasons.append(
                    f"runtime ledger slot_bindings.{slot_name}.target is invalid: {target}"
                )
        monitor_binding = slot_bindings.get("monitor")
        if not monitor_binding:
            reasons.append("runtime ledger slot_bindings.monitor is missing")
        else:
            monitor_role = normalize_role(monitor_binding.get("role"))
            monitor_target = normalize_target(monitor_binding.get("target"))
            if monitor_role != "qa-bot":
                warnings.append(
                    "runtime ledger slot_bindings.monitor.role is not qa-bot; "
                    f"actual={monitor_role or '<empty>'}"
                )
            if not monitor_target:
                reasons.append("runtime ledger slot_bindings.monitor.target is missing")

    return reasons, warnings
