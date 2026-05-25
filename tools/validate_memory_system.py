#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.memory_hook_gateway import build_context_package


def validate_memory_system(*, host: str = "codex", event: str = "session-start") -> dict[str, object]:
    previous = os.environ.get("MEMORY_HOOK_CORE_PROVIDER")
    os.environ["MEMORY_HOOK_CORE_PROVIDER"] = "legacy"
    try:
        package = build_context_package(host, event, {})
    finally:
        if previous is None:
            os.environ.pop("MEMORY_HOOK_CORE_PROVIDER", None)
        else:
            os.environ["MEMORY_HOOK_CORE_PROVIDER"] = previous
    return {
        "status": package.get("status"),
        "project_scope": package.get("project_scope"),
        "missing_paths": package.get("missing_paths", []),
        "validation_errors": package.get("validation_errors", []),
    }


def main() -> int:
    result = validate_memory_system()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    has_errors = bool(result["missing_paths"] or result["validation_errors"] or result["status"] != "ok")
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
