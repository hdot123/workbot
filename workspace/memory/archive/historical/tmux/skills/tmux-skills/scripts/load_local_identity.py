#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: Old identity mechanism has been deprecated
# Alternative: None (functionality deprecated)
# This file is retained for backward compatibility only.
# ==============================================================================

"""Deprecated compatibility stub for removed tmux-skills pane-session loading."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("load_local_identity.py")
# ==============================================================================


def main() -> int:
    raise SystemExit(
        "load_local_identity.py is deprecated: tmux-skills no longer manages pane-session bootstrap loading. "
        "Use pane_count + pane_titles with start_formal_runtime_chain.py instead."
    )


if __name__ == "__main__":
    raise SystemExit(main())
