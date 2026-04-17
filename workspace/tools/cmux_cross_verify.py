#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_summary_artifact import build_summary_artifact, write_summary_artifact


def run_cmux(*args: str) -> str:
    proc = subprocess.run(["cmux", *args], check=True, capture_output=True, text=True)
    return proc.stdout


def send_text(workspace_ref: str, surface_ref: str, text: str) -> None:
    run_cmux("send", "--workspace", workspace_ref, "--surface", surface_ref, text)
    run_cmux("send-key", "--surface", surface_ref, "Enter")


def read_screen(workspace_ref: str, surface_ref: str, lines: int = 260) -> str:
    return run_cmux(
        "read-screen",
        "--workspace",
        workspace_ref,
        "--surface",
        surface_ref,
        "--scrollback",
        "--lines",
        str(lines),
    )


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        ch = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    return None


def parse_marker_json(screen: str, marker: str) -> dict[str, object] | None:
    search_from = len(screen)
    while True:
        idx = screen.rfind(marker, 0, search_from)
        if idx < 0:
            return None
        payload = screen[idx + len(marker) :]
        json_candidate = _extract_first_json_object(payload)
        if json_candidate:
            try:
                parsed = json.loads(json_candidate)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
        search_from = idx


def parse_ok(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "ok", "pass", "passed"}
    return False


def wait_result(workspace_ref: str, surface_ref: str, marker: str, timeout_s: float) -> tuple[dict[str, object] | None, str]:
    deadline = time.monotonic() + timeout_s
    latest = ""
    while time.monotonic() < deadline:
        latest = read_screen(workspace_ref, surface_ref)
        parsed = parse_marker_json(latest, marker)
        if parsed is not None:
            return parsed, latest
        time.sleep(0.4)
    return None, latest


def run_check(
    workspace_ref: str,
    surface_ref: str,
    marker: str,
    prompt: str,
    timeout_s: float,
    retries: int,
) -> tuple[dict[str, object] | None, str, int]:
    latest = ""
    for attempt in range(1, retries + 1):
        send_text(workspace_ref, surface_ref, prompt)
        parsed, latest = wait_result(workspace_ref, surface_ref, marker, timeout_s)
        if parsed is not None:
            return parsed, latest, attempt
    return None, latest, retries


def load_surface_map(runtime_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for bot in ("pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot"):
        manifest = runtime_dir / f"runtime-launch-manifest-{bot}.json"
        if not manifest.exists():
            continue
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        surface_ref = str(payload.get("surface_ref") or "").strip()
        if surface_ref:
            mapping[bot] = surface_ref
    return mapping


def build_cross_verify_summary(report: dict[str, object], report_path: Path | None) -> dict[str, object]:
    overall = str(report.get("overall") or "failed").strip().lower() or "failed"
    failed = [str(item).strip() for item in report.get("failed_checks") or [] if str(item).strip()]
    check_count = len(report.get("checks") or {})
    if overall == "passed":
        summary_lines = [
            f"Cross verification passed across {check_count} checks.",
            "Commander should read this summary first; raw check payloads remain sidecar-only.",
        ]
    else:
        rendered_failed = ", ".join(failed[:3]) if failed else "unknown checks"
        if len(failed) > 3:
            rendered_failed = f"{rendered_failed}, +{len(failed) - 3} more"
        summary_lines = [
            f"Cross verification failed across {len(failed) or 1} checks.",
            f"Failed checks: {rendered_failed}.",
        ]
    return build_summary_artifact(
        title="cmux cross verification",
        status=overall if overall in {"passed", "failed"} else "failed",
        summary_lines=summary_lines,
        source="cmux_cross_verify",
        primary_sidecar_path=str(report_path) if report_path else None,
        sidecar_paths=[str(report_path)] if report_path else [],
        extra={
            "failed_checks": failed,
            "overall": overall,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-verify cmux bot MCP health after runtime changes.")
    parser.add_argument("--workspace", required=True, help="cmux workspace ref, e.g. workspace:47")
    parser.add_argument("--project-dir", default="/Users/busiji/workbot")
    parser.add_argument("--timeout-seconds", type=float, default=70.0)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    runtime_dir = project_dir / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    surface_map = load_surface_map(runtime_dir)

    required = {"pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot"}
    missing = sorted(required - set(surface_map))
    if missing:
        raise RuntimeError(f"missing runtime launch manifest for: {', '.join(missing)}")

    run_id = uuid.uuid4().hex[:8]
    marker_num = 0

    report: dict[str, object] = {
        "run_id": run_id,
        "workspace_ref": args.workspace,
        "project_dir": str(project_dir),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checks": {},
    }

    # 1) All bots: claude_code read check.
    for bot in ("dev-bot", "qa-bot", "doc-bot", "rea-bot", "pm-bot"):
        surface = surface_map[bot]
        target = project_dir / ".claude" / "agents" / f"{bot}.md"
        marker_num += 1
        marker = f"XC{run_id}{marker_num}:"
        prompt = (
            f"请只调用一次 mcp__claude_code__Read 读取 {target}。"
            f"完成后只输出一行，不要解释：{marker}"
            '{"bot":"%s","check":"read","ok":1}'
        ) % bot
        parsed, screen, attempts = run_check(args.workspace, surface, marker, prompt, args.timeout_seconds, max(1, args.retries))
        key = f"{bot}:claude_read"
        if parsed is None:
            report["checks"][key] = {
                "status": "failed",
                "reason": "timeout",
                "attempts": attempts,
                "marker": marker,
                "screen_tail": screen.splitlines()[-20:],
            }
            continue
        ok = parse_ok(parsed.get("ok"))
        report["checks"][key] = {
            "status": "passed" if ok else "failed",
            "attempts": attempts,
            "marker": marker,
            "result": parsed,
        }

    # 2) pm-bot: crawl4ai md check.
    pm_surface = surface_map["pm-bot"]
    marker_num += 1
    marker = f"XC{run_id}{marker_num}:"
    crawl_timeout = max(args.timeout_seconds * 2, 90.0)
    prompt = (
        "请只调用一次 mcp__crawl4ai__md，参数 "
        '{"params":"{\\"url\\":\\"https://docs.crawl4ai.com/core/quickstart/\\"}"}。'
        f"完成后只输出一行，不要解释：{marker}"
        '{"bot":"pm-bot","check":"crawl","ok":1,"code":200}'
    )
    parsed, screen, attempts = run_check(args.workspace, pm_surface, marker, prompt, crawl_timeout, max(1, args.retries))
    key = "pm-bot:crawl4ai_md"
    if parsed is None:
        report["checks"][key] = {
            "status": "failed",
            "reason": "timeout",
            "attempts": attempts,
            "marker": marker,
            "screen_tail": screen.splitlines()[-20:],
        }
    else:
        code = str(parsed.get("code") or "").strip()
        ok = parse_ok(parsed.get("ok")) and code == "200"
        report["checks"][key] = {
            "status": "passed" if ok else "failed",
            "attempts": attempts,
            "marker": marker,
            "result": parsed,
        }

    failed = [k for k, v in (report.get("checks") or {}).items() if isinstance(v, dict) and v.get("status") != "passed"]
    report["overall"] = "passed" if not failed else "failed"
    report["failed_checks"] = failed

    out_path = runtime_dir / "cross-verify-latest.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = runtime_dir / "cross-verify-summary-latest.json"
    summary_artifact = build_cross_verify_summary(report, out_path)
    write_summary_artifact(summary_path, summary_artifact)
    print(
        json.dumps(
            {
                "overall": report["overall"],
                "failed_checks": failed,
                "summary_path": str(summary_path),
                "report_path": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
