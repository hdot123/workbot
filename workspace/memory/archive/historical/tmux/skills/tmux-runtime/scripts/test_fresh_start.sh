#!/bin/bash
#
# Fresh Start Acceptance Test Script
# Executes tmux runtime startup from external visible terminal
# Records total elapsed time and phase timings
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKBOT_ROOT="/Users/busiji/workbot"
TIMING_LOG="/tmp/tmux-fresh-start-timing.json"
OUTPUT_LOG="/tmp/tmux-fresh-start-output.log"
LAUNCH_MARKER="/tmp/tmux-fresh-start.launch"

now_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

wait_for_tmux_server_gone() {
  local attempts=20
  local delay=0.05
  local i
  for ((i = 0; i < attempts; i++)); do
    if ! tmux list-sessions >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  return 0
}

rm -f "$TIMING_LOG" "$OUTPUT_LOG" "$LAUNCH_MARKER"
exec > >(tee "$OUTPUT_LOG") 2>&1

# Generate a unique thread ID for this test
TEST_THREAD_ID="test-$(date +%Y%m%d-%H%M%S)-$$"

echo "=============================================="
echo "tmux-runtime Fresh Start Acceptance Test"
echo "=============================================="
echo "Test Thread ID: $TEST_THREAD_ID"
echo "Start Time: $(date -Iseconds)"
echo "Timing Log: $TIMING_LOG"
echo ""

# Record start time
START_TIME=$(now_ms)

# Kill any existing tmux sessions to ensure fresh start
echo "[Pre-flight] Killing existing tmux sessions..."
tmux kill-server 2>/dev/null || true
wait_for_tmux_server_gone

# Clean up any existing watcher processes
echo "[Pre-flight] Stopping existing watcher processes..."
pkill -f "watch_tmux_handoff.py" 2>/dev/null || true

# Clean up runtime artifacts
echo "[Pre-flight] Cleaning up runtime artifacts..."
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/current-runtime.json
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/last-runtime-issues.json
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/handoff-notifications.jsonl
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/handoff-notifications.sqlite3
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/watch-tmux-handoff.stdout.log
rm -f /Users/busiji/workbot/workspace/artifacts/tmux-runtime/start-formal-runtime-chain.stdout.log

echo ""
echo "[Startup] Launching tmux runtime chain..."
echo ""

echo "[Launcher] Writing runtime result to: $TIMING_LOG"
echo "[Launcher] The attached tmux client will stay open after READY."
printf '%s\n' "$(date -Iseconds)" > "$LAUNCH_MARKER"

TMUX_START_RESULT_PATH="$TIMING_LOG" \
TMUX_START_TEST_START_MS="$START_TIME" \
python3 "$SCRIPT_DIR/start_formal_runtime_chain.py" \
  --codex-thread-id "$TEST_THREAD_ID" \
  --formal-session formal-session \
  --pane-title dev-bot \
  --pane-title dev-bot \
  --pane-title doc-bot \
  --pane-title doc-bot \
  --pretty
