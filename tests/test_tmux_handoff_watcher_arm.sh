#!/usr/bin/env bash

set -euo pipefail

SCRIPT="/Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py"

if ! command -v tmux >/dev/null 2>&1; then
  echo "skip: tmux command not found"
  exit 0
fi

attached_session="$(
  { tmux list-sessions -F '#{session_name} #{session_attached}' 2>/dev/null || true; } \
    | awk '$2 > 0 {print $1; exit}'
)"
if [[ -z "${attached_session}" ]]; then
  echo "skip: requires an attached formal session for watcher arming"
  exit 0
fi

target="$(tmux list-panes -t "${attached_session}" -F '#{session_name}:#{window_index}.#{pane_index}' | head -n 1)"
if [[ -z "${target}" ]]; then
  echo "fail: no pane found in attached session ${attached_session}"
  exit 1
fi

tmux set-environment -g CODEX_THREAD_ID "test-thread-id"
tmp_json="$(mktemp)"
trap 'rm -f "'"${tmp_json}"'" >/dev/null 2>&1 || true' EXIT

python3 "${SCRIPT}" \
  --formal-session-name "${attached_session}" \
  --target "${target}" \
  --dry-run \
  --pretty >"${tmp_json}"

if ! grep -q "\"status\": \"dry_run\"" "${tmp_json}"; then
  echo "fail: expected dry_run status"
  cat "${tmp_json}"
  exit 1
fi

if ! grep -q "\"${target}\"" "${tmp_json}"; then
  echo "fail: expected target ${target} in output"
  cat "${tmp_json}"
  exit 1
fi

if ! grep -q "watch_tmux_handoff.py" "${tmp_json}"; then
  echo "fail: expected watcher command in output"
  cat "${tmp_json}"
  exit 1
fi

echo "ok: watcher arming dry-run honors attached formal-session precondition"
