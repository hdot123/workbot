#!/usr/bin/env python3
"""
P2 Linear Task Publication Script
Creates P2 project, 8 implementation issues, 9 acceptance issues,
dependencies, and mandatory comments — all in Backlog, no mutations.

Usage:
  export LINEAR_API_KEY="$(op item get 'API 凭据-linear' --vault sever --field credential --reveal)"
  python3 scripts/p2-linear-publish.py
"""

import json
import os
import subprocess
import sys

# ── Config ──────────────────────────────────────────────────────────
API = "https://api.linear.app/graphql"
DNS_TARGET = "api.linear.app:443:172.64.147.211"  # DNS fallback from P1 sessions
TEAM_ID = "62318e54-d65f-42bd-8d31-7a1f0e146cae"  # JTO team
TEAM_KEY = "JTO"
PROJECT_NAME = "P2 — Long-task dry-run + GitLab CI feedback loop"

MANDATORY_COMMENT = """\
This is a P2 dry-run/planning issue.
No real Factory dispatch is allowed.
No GitHub push is allowed.
No Linear state/label mutation is allowed.
GitLab CI remains required before any real execution.
Acceptance issue is required before closure."""

# ── GraphQL helper via curl ─────────────────────────────────────────

def gql(query: str, variables: dict | None = None, retries: int = 3) -> dict:
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        print("FATAL: LINEAR_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    body = {"query": query}
    if variables:
        body["variables"] = variables
    body_json = json.dumps(body)
    last_err = ""
    for attempt in range(retries):
        cmd = (
            f'curl -s --max-time 30 '
            f'--resolve "{DNS_TARGET}" '
            f'-X POST {API} '
            f'-H "Content-Type: application/json" '
            f'-H "Authorization: {api_key}" '
            f'-d \'{body_json}\''
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            break
        last_err = f"curl exit {result.returncode}: {result.stderr[:200]}"
        if attempt < retries - 1:
            import time
            time.sleep(2 ** attempt)
            print(f"    Retry {attempt + 2}/{retries}...", file=sys.stderr)
    else:
        print(f"gql failed after {retries} attempts: {last_err}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}\nRaw output: {result.stdout[:500]}", file=sys.stderr)
        sys.exit(1)
    if "errors" in data:
        for err in data["errors"]:
            print(f"GraphQL error: {err.get('message', err)}", file=sys.stderr)
        sys.exit(1)
    return data["data"]


def get_or_create_project(name: str) -> str:
    """Return project ID. Reuse if exists."""
    data = gql('query { projects { nodes { id name } } }')
    for p in data["projects"]["nodes"]:
        if p["name"] == name:
            print(f"  Reused project: {name} ({p['id']})")
            return p["id"]
    data = gql(
        'mutation CreateProject($input: ProjectCreateInput!) { projectCreate(input: $input) { success project { id name } } }',
        {"input": {"name": name, "teamIds": [TEAM_ID]}},
    )
    pid = data["projectCreate"]["project"]["id"]
    print(f"  Created project: {name} ({pid})")
    return pid


def create_issue(title: str, description: str, project_id: str) -> tuple[str, str]:
    """Create issue in Backlog. Return (issue_id, identifier). Idempotent — skips if exists."""
    # Check for duplicate by title in project (Linear uses "issues" query)
    q = gql(
        'query($pid: String!) { issues(filter: { project: { id: { eq: $pid } } }) { nodes { id identifier title } } }',
        {"pid": project_id}
    )
    for existing in q["issues"]["nodes"]:
        if existing["title"] == title:
            print(f"  Skipped (already exists): {existing['identifier']} ({existing['id']})")
            return existing["id"], existing["identifier"]
    data = gql(
        'mutation CreateIssue($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier } } }',
        {"input": {
            "teamId": TEAM_ID,
            "title": title,
            "description": description,
            "projectId": project_id,
        }},
    )
    issue = data["issueCreate"]["issue"]
    print(f"  Created issue: {issue['identifier']} ({issue['id']})")
    return issue["id"], issue["identifier"]


def add_comment(issue_id: str, body: str) -> None:
    gql(
        'mutation Comment($input: CommentCreateInput!) { commentCreate(input: $input) { success } }',
        {"input": {"issueId": issue_id, "body": body}},
    )
    print(f"    Comment added to {issue_id}")


def set_dependency(issue_id: str, blocks_id: str) -> None:
    """issue_id depends on (is blocked by) blocks_id."""
    gql(
        'mutation Dep($input: IssueRelationCreateInput!) { issueRelationCreate(input: $input) { success } }',
        {"input": {"issueId": issue_id, "relatedIssueId": blocks_id, "type": "blocked_by"}},
    )
    print(f"    Dependency: {issue_id} blocked_by {blocks_id}")


# ── Issue bodies ────────────────────────────────────────────────────

def p2_01_body() -> str:
    return """\
## P2-01 — Define long-task dry-run contract

### 背景
P1 Linear → Factory Dispatch dry-run 闭环已归档。P2 需要定义长任务 dry-run 的任务契约。

### 目标
定义 Factory 长任务 dry-run 的任务契约，不真实执行。

### 内容覆盖
1. long_task=true
2. dry_run=true
3. no_write=true
4. no_push=true
5. no_deploy=true
6. github_push_forbidden=true
7. required_ci=gitlab
8. max_fix_attempts=3
9. checkpoint_required=true
10. runlog_required=true
11. heartbeat_required=true
12. acceptance_required=true

### 禁止事项
- 不允许真实 Factory dispatch
- 不允许 GitHub push
- 不允许 Linear 状态/标签变更
- 不包含任何 secret
- 不允许改代码

### 交付物
- long-task dry-run contract markdown
- payload 字段清单
- 禁止真实执行规则
- 与 P1 dispatch payload 的差异表

### 验收标准
- 不包含任何 secret
- 不允许真实 Factory dispatch
- 不允许 GitHub push
- 不允许 Linear 状态/标签变更
- 明确定义 stop condition
- 明确定义 max_fix_attempts

### 依赖
- P1 closure report

### 是否允许改代码
否，先文档设计

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""


def p2_02_body() -> str:
    return """\
## P2-02 — Design subagent checkpoint / runlog / heartbeat policy

### 背景
长任务中子代理可能中途停止、无证据停止、静默长命令，需要设计执行策略。

### 目标
解决长任务中子代理中途停止、无证据停止、静默长命令的问题。

### 内容覆盖
1. checkpoint 文件格式
2. runlog 文件路径
3. heartbeat 输出策略
4. 长命令 tee / verbose / timeout 规范
5. SubagentStop 处理原则
6. block / allow 停止条件
7. 父代理如何恢复中断任务
8. acceptance 子代理如何审查 runlog

### 禁止事项
- 不允许无证据停止
- 不允许无限循环
- 不允许改代码

### 交付物
- subagent long-task execution policy
- checkpoint schema
- runlog examples
- stop-condition matrix

### 验收标准
- 子代理不能无证据停止
- 长命令不能静默超过 60 秒
- 每个阶段必须有 checkpoint
- BLOCKED 必须有命令/日志/错误证据
- 不允许无限循环

### 是否允许改代码
否，先文档设计

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""


def p2_03_body() -> str:
    return """\
## P2-03 — Design GitLab pipeline result provider contract

### 背景
需要设计 GitLab pipeline result → webhook-ingress 的 provider contract。

### 目标
设计 GitLab pipeline result → webhook-ingress 的 provider contract，先 disabled，不启用。

### 内容覆盖
1. provider=gitlab
2. supported events: pipeline, job, push, merge_request
3. canonical_type mapping
4. pipeline_id, commit_sha, branch, status, project_id
5. delivery_id / event_id
6. signature / token verification
7. idempotency key
8. disabled-by-default policy

### 禁止事项
- 不创建 webhook
- 不启用 provider
- 不创建 APISIX route
- 不调用 GitLab API 写操作
- 不输出 token/secret
- 不允许改代码

### 交付物
- GitLab provider contract
- canonical event mapping
- disabled route plan
- validation checklist

### 验收标准
- 不创建 webhook
- 不启用 provider
- 不创建 APISIX route
- 不调用 GitLab API 写操作
- 不输出 token/secret
- 明确只做 design/dry-run

### 是否允许改代码
否，先设计

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""


def p2_04_body() -> str:
    return """\
## P2-04 — Design GitLab CI result → Linear dry-run comment flow

### 背景
需要设计 pipeline 结果如何回写 Linear，但只允许 comment。

### 目标
设计 pipeline success/failure 如何回写 Linear，但只允许 comment，不允许 issueUpdate。

### 链路
GitLab pipeline event → webhook-ingress → canonical event → audit log → Linear dry-run comment

### 评论必须包含
1. pipeline_id
2. pipeline_status
3. commit_sha
4. branch
5. GitLab CI result
6. no Linear status mutation
7. no label mutation
8. no GitHub push

### 禁止事项
- 不允许改状态
- 不允许改标签
- 不允许自动触发 Factory 修复
- 不允许 GitHub push
- 不允许改代码

### 交付物
- flow design
- comment template
- failure/success examples
- audit fields

### 验收标准
- 只允许 Linear comment
- 不允许改状态
- 不允许改标签
- 不允许自动触发 Factory 修复
- 不允许 GitHub push

### 是否允许改代码
否，先设计

### 是否需要 GitLab CI
否

### 是否允许真实 Factory dispatch
否
"""


def p2_05_body() -> str:
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


def p2_06_body() -> str:
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


def p2_07_body() -> str:
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


def p2_08_body() -> str:
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


def ac_body(ac_id: str, target: str, criteria: list[str]) -> str:
    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    return f"""\
## {ac_id} — Accept {target}

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
    print("=== P2 Linear Task Publication ===\n")

    # 1. Create/reuse project
    print("[1] Creating/reusing P2 project...")
    project_id = get_or_create_project(PROJECT_NAME)

    # 2. Create implementation issues
    print("\n[2] Creating 8 implementation issues...")
    impl_issues = {}
    impl_defs = [
        ("P2-01 — Define long-task dry-run contract", p2_01_body),
        ("P2-02 — Design subagent checkpoint / runlog / heartbeat policy", p2_02_body),
        ("P2-03 — Design GitLab pipeline result provider contract", p2_03_body),
        ("P2-04 — Design GitLab CI result → Linear dry-run comment flow", p2_04_body),
        ("P2-05 — Design Factory real-dispatch gate", p2_05_body),
        ("P2-06 — Design Linear issueUpdate / label mutation dry-run gate", p2_06_body),
        ("P2-07 — Design persistent audit upgrade path", p2_07_body),
        ("P2-08 — Create P2 dry-run tabletop scenario", p2_08_body),
    ]
    for label, body_fn in impl_defs:
        iid, ident = create_issue(label, body_fn(), project_id)
        impl_issues[label.split(" — ")[0]] = {"id": iid, "identifier": ident}

    # 3. Create acceptance issues
    print("\n[3] Creating 9 acceptance issues...")
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

    ac_issues = {}
    for label, target, criteria in ac_defs:
        ac_id = label.split(" — ")[0]
        iid, ident = create_issue(label, ac_body(ac_id, target, criteria), project_id)
        ac_issues[ac_id] = {"id": iid, "identifier": ident, "target": target}

    # 4. Set dependencies
    print("\n[4] Setting dependencies...")

    # P2-AC-01..08 depends on P2-01..08
    for i in range(1, 9):
        ac_key = f"P2-AC-{i:02d}"
        impl_key = f"P2-{i:02d}"
        set_dependency(ac_issues[ac_key]["id"], impl_issues[impl_key]["id"])

    # P2-AC-09 depends on P2-AC-01..08
    for i in range(1, 9):
        ac_key = f"P2-AC-{i:02d}"
        set_dependency(ac_issues["P2-AC-09"]["id"], ac_issues[ac_key]["id"])

    # P2-08 depends on P2-01..07
    for i in range(1, 8):
        impl_key = f"P2-{i:02d}"
        set_dependency(impl_issues["P2-08"]["id"], impl_issues[impl_key]["id"])

    # 5. Add mandatory comments
    print("\n[5] Adding mandatory comments...")
    all_issues = {**impl_issues, **ac_issues}
    for key, info in all_issues.items():
        add_comment(info["id"], MANDATORY_COMMENT)

    # 6. Output results as JSON for report generation
    print("\n[6] Outputting results...")
    output = {
        "project_id": project_id,
        "project_name": PROJECT_NAME,
        "impl_issues": {k: v for k, v in impl_issues.items()},
        "ac_issues": {k: {kk: vv for kk, vv in v.items() if kk != "target"} for k, v in ac_issues.items()},
    }
    # Write to a temp JSON for report generation (no secrets)
    result_path = "/Users/busiji/workbot/scripts/p2-linear-publish-result.json"
    with open(result_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to {result_path}")
    print(f"\n=== Publication complete ===")
    print(f"  Implementation issues: {len(impl_issues)}")
    print(f"  Acceptance issues: {len(ac_issues)}")
    print(f"  Total comments added: {len(all_issues)}")


if __name__ == "__main__":
    main()
