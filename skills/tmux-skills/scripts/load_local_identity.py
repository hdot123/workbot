#!/usr/bin/env python3
"""Deprecated compatibility stub for removed tmux-skills pane-session loading."""

from __future__ import annotations


def main() -> int:
    raise SystemExit(
        "load_local_identity.py is deprecated: tmux-skills no longer manages pane-session bootstrap loading. "
        "Use pane_count + pane_titles with start_formal_runtime_chain.py instead."
    )


if __name__ == "__main__":
    raise SystemExit(main())
