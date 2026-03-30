#!/usr/bin/env bash

set -euo pipefail

ROOT="/Users/busiji/workbot"
CHAIN_SCRIPT="${ROOT}/skills/tmux-skills/scripts/start_formal_runtime_chain.py"
FORMAL_SESSION="${FORMAL_SESSION:-formal-session}"
FORMAL_PANE_TITLES="${FORMAL_PANE_TITLES:-task-1,task-2,notes,monitor}"
PANE_COUNT="$(awk -F',' '{print NF}' <<<"${FORMAL_PANE_TITLES}")"

if [[ -z "${1:-}" || -z "${2:-}" ]]; then
  echo "错误: 请同时提供当天的 TASK_THREAD_ID 和 MONITOR_THREAD_ID" >&2
  echo "用法: ./scripts/start-day.sh <TASK_THREAD_ID> <MONITOR_THREAD_ID> [TASK_ID]" >&2
  exit 1
fi

TASK_THREAD_ID="$1"
MONITOR_THREAD_ID="$2"
TASK_ID="${3:-start-day-formal-runtime}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "错误: tmux 不可用" >&2
  exit 1
fi

if [[ ! -f "${CHAIN_SCRIPT}" ]]; then
  echo "错误: 串联入口不存在: ${CHAIN_SCRIPT}" >&2
  exit 1
fi

echo "执行 tmux-skills 串联入口 (env -> topology -> pane-labeling -> ledger -> watcher)..."
echo "tmux-skills 将创建或接管前台 formal-session，并生成 ${PANE_COUNT} 个 pane。"
echo "任务线程: ${TASK_THREAD_ID}"
echo "监控线程: ${MONITOR_THREAD_ID}"
python3 "${CHAIN_SCRIPT}" \
  --codex-thread-id "${MONITOR_THREAD_ID}" \
  --formal-session "${FORMAL_SESSION}" \
  --pane-count "${PANE_COUNT}" \
  $(for title in ${FORMAL_PANE_TITLES//,/ }; do printf '%s ' "--pane-title" "$title"; done) \
  --task-id "${TASK_ID}" \
  --pretty
