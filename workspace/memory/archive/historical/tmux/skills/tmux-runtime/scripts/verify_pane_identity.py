#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: Integrated into init_tmux_panes.py
# Alternative: Use init_tmux_panes.py instead
# This file is retained for backward compatibility only.
# ==============================================================================

"""Deprecated compatibility stub for removed tmux-runtime pane-session verification (DEPRECATED)."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("verify_pane_identity.py")
# ==============================================================================


def main() -> int:
    raise SystemExit(
        "verify_pane_identity.py is deprecated: tmux-runtime no longer verifies external session markers. "
        "Use init_tmux_panes.py to apply pane titles and check_tmux_ready.py for tmux-only validation."
    )


if __name__ == "__main__":
    raise SystemExit(main())
