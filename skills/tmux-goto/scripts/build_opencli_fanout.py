#!/usr/bin/env python3
"""Compatibility shim for legacy opencli fanout. Use build_tmux_goto_bundle.py directly."""
from __future__ import annotations

import sys
import warnings

# Emit deprecation warning to stderr at module load time
sys.stderr.write(
    "WARNING: build_opencli_fanout.py is deprecated. Use build_tmux_goto_bundle.py directly.\n"
)
sys.stderr.flush()

from build_tmux_goto_bundle import main

if __name__ == "__main__":
    raise SystemExit(main())
