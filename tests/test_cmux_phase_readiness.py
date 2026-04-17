#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.cmux_phase_readiness import (
    collect_delivery_doc_anchor_problems,
    collect_project_status_map,
    collect_project_status_problems,
    extract_delivery_anchor_paths,
    extract_absolute_paths,
)


def test_extract_absolute_paths_collects_unique_user_paths() -> None:
    text = """
    - `/Users/busiji/workbot/a.md`
    - `/Users/busiji/workbot/b.md`
    - `/Users/busiji/workbot/a.md`
    """
    assert extract_absolute_paths(text) == [
        "/Users/busiji/workbot/a.md",
        "/Users/busiji/workbot/b.md",
    ]


def test_collect_delivery_doc_anchor_problems_flags_missing_refs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        present = repo_root / "workspace" / "INDEX.md"
        missing = repo_root / "workspace" / "does-not-exist.md"
        doc = root / "delivery.md"
        doc.write_text(
            "\n".join(
                [
                    "## Repo Artifact Added by This Delivery",
                    f"- `{present}`",
                    f"- `{missing}`",
                ]
            ),
            encoding="utf-8",
        )
        problems = collect_delivery_doc_anchor_problems((doc,))
        assert problems[str(doc)] == [str(missing)]


def test_extract_delivery_anchor_paths_ignores_non_delivery_sections() -> None:
    present = repo_root / "workspace" / "INDEX.md"
    text = "\n".join(
        [
            "## Remaining Omissions Not Fixed",
            f"- `{repo_root / 'workspace' / 'missing.md'}`",
            "## Repo Artifact Added by This Delivery",
            f"- `{present}`",
        ]
    )
    assert extract_delivery_anchor_paths(text) == [str(present)]


def test_collect_project_status_map_parses_title_and_status() -> None:
    raw = json.dumps(
        {
            "items": [
                {"title": "[Phase 0] P10-core Dispatch gate contract", "status": "Done"},
                {"title": "[Phase 1] P1 Control packet schema", "status": "Done"},
            ]
        }
    )
    status_map = collect_project_status_map(raw)
    assert status_map["[Phase 0] P10-core Dispatch gate contract"] == "Done"
    assert status_map["[Phase 1] P1 Control packet schema"] == "Done"


def test_collect_project_status_problems_reports_non_done_titles() -> None:
    status_map = {
        "[Phase 0] P10-core Dispatch gate contract": "Done",
        "[Phase 1] P1 Control packet schema": "Todo",
    }
    problems = collect_project_status_problems(
        status_map,
        (
            "[Phase 0] P10-core Dispatch gate contract",
            "[Phase 1] P1 Control packet schema",
            "[Phase 1] P2 Summary and sidecar split",
        ),
    )
    assert problems == [
        "[Phase 1] P1 Control packet schema => Todo",
        "[Phase 1] P2 Summary and sidecar split => missing",
    ]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
