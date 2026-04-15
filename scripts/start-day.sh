#!/usr/bin/env bash

set -euo pipefail

ROOT="/Users/busiji/workbot"
CMUX_BOOTSTRAP="/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py"

echo "错误: tmux runtime 已退役，本仓库仅允许 cmux。" >&2
echo "请改用: python3 ${CMUX_BOOTSTRAP} --project-dir ${ROOT} --recreate" >&2
exit 2
