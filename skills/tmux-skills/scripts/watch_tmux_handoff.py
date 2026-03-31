#!/usr/bin/env python3
"""Watch tmux panes and report stopped or unreachable panes to the CODEX_THREAD_ID-bound Codex thread."""

from __future__ import annotations

# pane_stopped 统一口径：
# 1. pane_dead > 0
# 2. 不再使用"输出长时间无变化"作为停止依据，因为空闲 shell / 等待输入的 pane 仍然是活着的
# 3. 会话脱离前台和 pane 不可达分别上报为 session_detached / pane_unreachable

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
import sys
import time
from pathlib import Path
from typing import Any

from runtime_ledger import CURRENT_RUNTIME_LEDGER_PATH


DEFAULT_POLL_INTERVAL_SECONDS = 10.0
DEFAULT_CAPTURE_START = -5
DEFAULT_DELIVERY_QUEUE_DIR = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/delivery-queue"
)
DEFAULT_DELIVERY_STDOUT_LOG = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/deliver-tmux-handoff.stdout.log"
)
DEFAULT_BRIDGE_PID_FILE = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/tmux-handoff-app-bridge.pid"
)
DEFAULT_RECEIPTS_LOG = Path(
    "/Users/busiji/workbot/workspace/artifacts/tmux-skills/handoff-delivery-receipts.jsonl"
)

