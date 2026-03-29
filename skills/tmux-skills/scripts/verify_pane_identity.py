#!/usr/bin/env python3
"""Deprecated compatibility stub for removed tmux-skills pane identity verification."""

from __future__ import annotations


def main() -> int:
    raise SystemExit(
        "verify_pane_identity.py is deprecated: tmux-skills no longer verifies Claude scenes or identities. "
        "Use init_tmux_panes.py to apply pane titles and check_tmux_ready.py for tmux-only validation."
    )


if __name__ == "__main__":
    raise SystemExit(main())
