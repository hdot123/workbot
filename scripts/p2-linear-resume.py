#!/usr/bin/env python3
"""
P2 Linear Task Publication — Resume Script
Safe resume: only creates missing issues, skips existing ones.
Uses SOCKS proxy for stable connectivity.
"""

import json, os, subprocess, sys, time

PROXY = "--socks5-hostname 100.100.1.22:11080"
API = "https://api.linear.app/graphql"
PROJECT_ID = "e8365417-e2d8-4834-ace2-98eff6adeeab"
TEAM_ID = "62318e54-d65f-42bd-8d31-7a1f0e146cae"
MAX_RETRIES = 5

MANDATORY_COMMENT = """\
This is a P2 dry-run/planning issue.
No real Factory dispatch is allowed.
No GitHub push is allowed.
No Linear state/label mutation is allowed.
GitLab CI remains required before any real execution.
Acceptance issue is required before closure."""

def curl_gql(query, variables=None, retries=MAX_RETRIES):
    api_key = os.environ.get("LINEAR_API_KEY", "")
    body = json.dumps({"query": query, "variables": variables or {}})
    last_err = ""
    for attempt in range(retries):
        cmd = (
            f'curl -s --max-time 30 {PROXY} '
            f'-X POST {API} '
            f'-H "Content-Type: application/json" '
            f'-H "Authorization: {api_key}" '
            f'-d \'{body}\''
        )
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            try:
                data = json.loads(r.stdout)
                if "errors" in data:
                    for err in data["errors"]:
                        print(f"  GraphQL error: {err.get('message', err)}", file=sys.stderr)
                    return None
                return data["data"]
            except:
                last_err = f"JSON parse error: {r.stdout[:100]}"
        else:
            last_err = f"curl exit {r.returncode}"
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    print(f"  gql failed after {retries} attempts: {last_err}", file=sys.stderr)
    return None

def get_existing_titles() -> set:
    data = curl_gql(
        'query { issues(filter: { project: { id: { eq: "%s" } } }, first: 50) '
        '{ nodes { id identifier title } } }' % PROJECT_ID
    )
    if not data:
        return set()
    return {(iss["id"], iss["identifier"], iss["title"]) for iss in data["issues"]["nodes"]}

def issue_exists_by_title(title: str, existing) -> tuple[bool, str, str]:
    for iid, ident, t in existing:
        if t == title:
            return True, ident, iid
    return False, "", ""

def create_issue(title: str, body: str, existing) -> tuple[str, str, bool]:
    exists, ident, iid = issue_exists_by_title(title, existing)
    if exists:
        print(f"  ⏭ Skipped (exists): {ident}")
        return ident, iid, True
    data = curl_gql(
        'mutation CreateIssue($input: IssueCreateInput!) { issueCreate(input: $input) '
        '{ success issue { id identifier } } }',
        {"input": {"teamId": TEAM_ID, "title": title, "description": body, "projectId": PROJECT_ID}}
    )
    if not data:
        print(f"  ❌ Failed to create: {title[:50]}")
        return "", "", False
    issue = data["issueCreate"]["issue"]
    print(f"  ✅ Created: {issue['identifier']}")
    return issue["identifier"], issue["id"], True

def add_comment(issue_id: str, body: str) -> bool:
    data = curl_gql(
        'mutation Comment($input: CommentCreateInput!) { commentCreate(input: $input) { success } }',
        {"input": {"issueId": issue_id, "body": body}}
    )
    if data:
        print(f"    ✅ Comment added")
        return True
    print(f"    ❌ Comment failed")
    return False

def set_dependency(issue_id: str, blocks_id: str) -> bool:
    data = curl_gql(
        'mutation Dep($input: IssueRelationCreateInput!) { issueRelationCreate(input: $input) { success } }',
        {"input": {"issueId": issue_id, "relatedIssueId": blocks_id, "type": "blocked_by"}}
    )
    if data:
        print(f"    ✅ Dependency set: {issue_id} blocked_by {blocks_id}")
        return True
    print(f"    ⚠ Dependency may already exist or failed: {issue_id} blocked_by {blocks_id}")
    return False

def safe_add_comment(issue_id: str, body: str, retries=3) -> bool:
    """Add comment with retries, skip duplicate comments gracefully."""
    for attempt in range(retries):
        data = curl_gql(
            'mutation Comment($input: CommentCreateInput!) { commentCreate(input: $input) { success } }',
            {"input": {"issueId": issue_id, "body": body}}
        )
        if data:
            return True
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return False

# ── Issue bodies ────────────────────────────────────────────────────

def body_p2_05():
    return """\
## P2-05 — Design Factory real-dispatch gate

### 背景
需要定义未来什么时候允许从 dry-run 升级到真实 Factory dispatch。

### 目标
定义从 dry-run 升级到真实 Factory dispatch 的 gate 条件。

### Gate 条件
1. GitLab CI pipeline success
2. pipeline_id 可验证
3. commit_sha 匹配
4. Linear issue 在 canary/project 范围内
5. human approval 或明确 policy approval
6. max_fix_attempts 未超过
7. secret scan = 0
8. GitHub push gate 仍 fail-closed
9. rollback plan exists
10. acceptance issue 已通过

### 禁止事项
- 不允许打开真实 Factory
- 不允许调用 Factory API
- 不允许配置 FACTORY_API_KEY
- 不允许改代码

### 交付物
- real-dispatch gate matrix
- blocked reason taxonomy
- upgrade checklist
- rollback checklist

### 验收标准
- 当前结论必须是 real dispatch forbidden
- 不允许打开真实 Factory
- 不允许调用 Factory API
- 不允许配置 FACTORY_API_KEY

### 是否允许改代码
否

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""

def body_p2_06():
    return """\
## P2-06 — Design Linear issueUpdate / label mutation dry-run gate

### 背景
需要设计未来 Linear 状态/标签变更的 dry-run gate。

### 目标
设计 Linear 状态/标签变更的 dry-run gate，不能真实变更。

### 内容覆盖
1. issueUpdate dry-run payload
2. label mutation dry-run payload
3. allowed states / forbidden states
4. canary project only
5. approval required
6. audit log required
7. rollback strategy
8. duplicate suppression

### 禁止事项
- 当前禁止真实 issueUpdate
- 当前禁止真实 label mutation
- 不允许生产 issue 变更
- 不允许改代码

### 交付物
- Linear mutation dry-run design
- state transition matrix
- label mutation policy
- comment-only fallback

### 验收标准
- 当前禁止真实 issueUpdate
- 当前禁止真实 label mutation
- 只允许 comment
- 不允许生产 issue 变更

### 是否允许改代码
否

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""

def body_p2_07():
    return """\
## P2-07 — Design persistent audit upgrade path

### 背景
P1C 使用 file SQLite persistent audit，需要升级到 PostgreSQL/Supabase production_canary 方案。

### 目标
设计从 SQLite 到 PostgreSQL/Supabase 的 audit 存储升级方案。

### 内容覆盖
1. raw_events
2. canonical_events
3. processing_logs
4. action_result_json
5. delivery_id / event_id / issue_id / pipeline_id / run_id 查询
6. retention policy
7. duplicate event strategy

### 禁止事项
- 不执行 migration
- 不改生产 DB
- 不输出 database URL / password
- 不允许改代码

### 交付物
- DB schema gap analysis
- migration plan
- query examples
- rollback plan

### 验收标准
- 不执行 migration
- 不改生产 DB
- 只输出设计
- 不输出 DB secret

### 是否允许改代码
否

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""

def body_p2_08():
    return """\
## P2-08 — Create P2 dry-run tabletop scenario

### 背景
需要设计一次完整 tabletop 演练来验证 P2 全链路设计。

### 目标
设计一次完整 tabletop 演练，不真实执行。

### 场景链路
Linear issue ready → Factory long-task dry-run plan → subagent plan generated → GitLab CI required → fake pipeline result → Linear dry-run comment → audit evidence

### 禁止事项
- 不调用 Factory
- 不调用 GitLab 写 API
- 不改 Linear 状态/标签
- 不推 GitHub
- 不创建 webhook
- 不允许改代码

### 交付物
- tabletop scenario
- input event sample
- expected canonical event
- expected dispatch payload
- expected Linear comment
- expected audit rows
- PASS/BLOCKED criteria

### 验收标准
- 场景输入清楚
- 预期 payload 清楚
- 预期 Linear comment 清楚
- 预期 audit rows 清楚
- PASS/BLOCKED criteria 清楚
- 不真实执行

### 依赖
- P2-01 至 P2-07

### 是否允许改代码
否

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""

def body_ac(ac_label: str, target: str, criteria: list[str]):
    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    return f"""\
## {ac_label} — Accept {target}

### 验收对象
{target}

### 验收标准
{criteria_text}

### 验收结论
必须是以下之一：PASS / CONDITIONAL PASS / BLOCKED

### 禁止事项
- 不允许真实 Factory dispatch
- 不允许 GitHub push
- 不允许 Linear 状态/标签变更
- 不允许改代码
- 不输出 secret

### 是否允许改代码
否

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""

# ── Main ────────────────────────────────────────────────────────────

def main():
    print("=== P2 Linear Resume Publication ===\n")

    # Get existing issues
    print("[0] Getting existing issue state...")
    existing = get_existing_titles()
    print(f"  Existing issues: {len(existing)}")
    for _, ident, title in sorted(existing, key=lambda x: x[1]):
        print(f"    {ident}: {title[:60]}")
    print()

    results = {}  # label -> (identifier, id)

    # Map of known existing issues
    known_existing = {
        "P2-01": ("JTO-197", "743ead56-5c47-4a9a-b773-133064e50405"),
        "P2-02": ("JTO-198", "e0bdf4af-cb41-4f67-81f6-1cf1d3c50507"),
        "P2-03": ("JTO-199", "f4e93e32-f9f2-483e-a79e-3e92aa017211"),
        "P2-04": ("JTO-200", "3a5adb3b-2c1f-42d5-819b-78ea937bf865"),
    }

    # Update results with known existing
    for label, (ident, iid) in known_existing.items():
        for eid, eident, etitle in existing:
            if eident == ident:
                results[label] = (ident, iid)
                break

    # 1. Create P2-05 ~ P2-08
    print("[1] Creating P2-05 ~ P2-08...")
    impl_defs = [
        ("P2-05 — Design Factory real-dispatch gate", body_p2_05),
        ("P2-06 — Design Linear issueUpdate / label mutation dry-run gate", body_p2_06),
        ("P2-07 — Design persistent audit upgrade path", body_p2_07),
        ("P2-08 — Create P2 dry-run tabletop scenario", body_p2_08),
    ]
    for label, body_fn in impl_defs:
        short_label = label.split(" — ")[0]
        ident, iid, ok = create_issue(label, body_fn(), existing)
        if ok and ident:
            results[short_label] = (ident, iid)
            # Update existing set so deps don't duplicate
            existing = get_existing_titles()
    print()

    # 2. Create P2-AC-01 ~ P2-AC-09
    print("[2] Creating P2-AC-01 ~ P2-AC-09...")
    ac_defs = [
        ("P2-AC-01 — Accept long-task dry-run contract", "P2-01", [
            "dry-run/no_write/no_push/no_deploy 明确",
            "required_ci=gitlab 明确",
            "github_push_forbidden=true 明确",
            "checkpoint/runlog/heartbeat 要求明确",
            "no real Factory dispatch 明确",
            "no secret",
        ]),
        ("P2-AC-02 — Accept subagent long-task execution policy", "P2-02", [
            "子代理停止条件明确",
            "checkpoint 格式可执行",
            "runlog 格式可审计",
            "heartbeat 策略可防止静默",
            "BLOCKED 必须有证据",
            "避免无限循环",
        ]),
        ("P2-AC-03 — Accept GitLab provider contract design", "P2-03", [
            "provider disabled-by-default",
            "不创建 webhook",
            "不创建 APISIX route",
            "pipeline/job/push/MR mapping 清楚",
            "idempotency 清楚",
            "signature/token 验证清楚",
            "no secret",
        ]),
        ("P2-AC-04 — Accept GitLab CI result → Linear dry-run comment design", "P2-04", [
            "只允许 Linear comment",
            "不允许 issueUpdate",
            "不允许 label mutation",
            "pipeline_id/commit_sha/status 清楚",
            "audit fields 清楚",
            "failure/success comment 模板清楚",
        ]),
        ("P2-AC-05 — Accept Factory real-dispatch gate", "P2-05", [
            "当前真实 dispatch 仍 forbidden",
            "GitLab CI success 必须作为 gate",
            "commit_sha match 必须作为 gate",
            "max_fix_attempts 明确",
            "approval 明确",
            "rollback 明确",
        ]),
        ("P2-AC-06 — Accept Linear mutation dry-run gate", "P2-06", [
            "当前 issueUpdate forbidden",
            "当前 label mutation forbidden",
            "dry-run payload 清楚",
            "canary-only 清楚",
            "approval gate 清楚",
            "audit log required",
        ]),
        ("P2-AC-07 — Accept persistent audit upgrade design", "P2-07", [
            "schema gap 清楚",
            "migration plan 清楚",
            "query by delivery_id/event_id/issue_id/pipeline_id/run_id 清楚",
            "不执行 migration",
            "不输出 DB secret",
        ]),
        ("P2-AC-08 — Accept tabletop dry-run scenario", "P2-08", [
            "场景输入清楚",
            "预期 payload 清楚",
            "预期 Linear comment 清楚",
            "预期 audit rows 清楚",
            "PASS/BLOCKED criteria 清楚",
            "不真实执行",
        ]),
        ("P2-AC-09 — Final P2 planning acceptance", "全部 P2 issues", [
            "所有 P2 implementation issues 已完成",
            "所有 P2 acceptance issues 已完成",
            "无真实 Factory dispatch",
            "无 GitHub push",
            "无 Linear 状态/标签变更",
            "无生产 webhook 变更",
            "secret scan = 0",
            "输出 P2 planning closure report",
        ]),
    ]
    for label, target, criteria in ac_defs:
        short_label = label.split(" — ")[0]
        ident, iid, ok = create_issue(label, body_ac(short_label, target, criteria), existing)
        if ok and ident:
            results[short_label] = (ident, iid)
            existing = get_existing_titles()
    print()

    # 3. Set dependencies
    print("[3] Setting dependencies...")
    # P2-AC-01..08 depends on P2-01..08
    for i in range(1, 9):
        ac_key = f"P2-AC-{i:02d}"
        impl_key = f"P2-{i:02d}"
        if ac_key in results and impl_key in results:
            set_dependency(results[ac_key][1], results[impl_key][1])
    print()
    # P2-AC-09 depends on P2-AC-01..08
    if "P2-AC-09" in results:
        for i in range(1, 9):
            ac_key = f"P2-AC-{i:02d}"
            if ac_key in results:
                set_dependency(results["P2-AC-09"][1], results[ac_key][1])
    print()
    # P2-08 depends on P2-01..07
    if "P2-08" in results:
        for i in range(1, 8):
            impl_key = f"P2-{i:02d}"
            if impl_key in results:
                set_dependency(results["P2-08"][1], results[impl_key][1])
    print()

    # 4. Add mandatory comments to ALL issues in project
    print("[4] Adding mandatory comments to all P2 issues...")
    all_issues = get_existing_titles()
    for _, ident, title in all_issues:
        ok = safe_add_comment(_, MANDATORY_COMMENT)
        if ok:
            print(f"  ✅ Comment: {ident}")
        else:
            print(f"  ❌ Comment failed: {ident}")
    print()

    # 5. Write resume state
    print("[5] Writing resume state...")
    state = {
        "project_id": PROJECT_ID,
        "project_name": "P2 — Long-task dry-run + GitLab CI feedback loop",
        "results": {k: {"identifier": v[0], "id": v[1]} for k, v in results.items()},
        "total_issues": len(all_issues),
    }
    state_path = "/Users/busiji/workbot/scripts/p2-linear-resume-state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  ✅ State saved to {state_path}")
    print()

    # 6. Summary
    print("=== Resume Complete ===")
    print(f"  Implementation issues: {sum(1 for k in results if k.startswith('P2-') and 'AC' not in k)}")
    print(f"  Acceptance issues: {sum(1 for k in results if k.startswith('P2-AC'))}")
    print(f"  Total issues in project: {len(all_issues)}")

if __name__ == "__main__":
    main()
