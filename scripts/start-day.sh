#!/usr/bin/env bash

set -euo pipefail

ROOT="/Users/busiji/workbot"
CHAIN_SCRIPT="${ROOT}/skills/tmux-skills/scripts/start_formal_runtime_chain.py"
FORMAL_SESSION="${FORMAL_SESSION:-formal-session}"
FORMAL_PANE_TITLES="${FORMAL_PANE_TITLES:-dev-bot,dev-bot,qa-bot,doc-bot}"
PANE_COUNT="$(awk -F',' '{print NF}' <<<"${FORMAL_PANE_TITLES}")"

if [[ -z "${1:-}" ]]; then
  echo "错误: 请提供当天的 CODEX_THREAD_ID" >&2
  echo "用法: ./scripts/start-day.sh <CODEX_THREAD_ID> [TASK_ID]" >&2
  exit 1
fi

CODEX_THREAD_ID="$1"
TASK_ID="${2:-start-day-formal-runtime}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "错误: tmux 不可用" >&2
  exit 1
fi

if [[ ! -f "${CHAIN_SCRIPT}" ]]; then
  echo "错误: 串联入口不存在: ${CHAIN_SCRIPT}" >&2
  exit 1
fi

echo "执行正式串联入口 (env -> topology -> ledger -> watcher -> verify)..."
echo "前置条件: formal-session 必须已经准备成 ${PANE_COUNT} 个白名单 Claude 现场。"
python3 "${CHAIN_SCRIPT}" \
  --codex-thread-id "${CODEX_THREAD_ID}" \
  --formal-session "${FORMAL_SESSION}" \
  --pane-count "${PANE_COUNT}" \
  $(for title in ${FORMAL_PANE_TITLES//,/ }; do printf '%s ' "--pane-title" "$title"; done) \
  --task-id "${TASK_ID}" \
  --pretty
