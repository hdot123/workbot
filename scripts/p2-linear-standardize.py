#!/usr/bin/env python3
"""
P2 Linear Standardization Script
Creates standard labels, applies them to issues, updates project overview.
Does NOT modify issue state, does NOT create duplicate issues.
"""

import json, os, subprocess, sys, time

API = "https://api.linear.app/graphql"
TEAM_ID = "62318e54-d65f-42bd-8d31-7a1f0e146cae"
PROJECT_ID = "e8365417-e2d8-4834-ace2-98eff6adeeab"
PROXY = "--socks5-hostname 100.100.1.22:11080"

def gql(query, variables=None, retries=3):
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        print("FATAL: LINEAR_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    body = json.dumps({"query": query, "variables": variables or {}})
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
                return data.get("data")
            except Exception as e:
                print(f"  JSON parse error: {e}", file=sys.stderr)
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return None

# ── Step 1: Create standard labels ──────────────────────────────────
LABELS_TO_CREATE = [
    {"name": "phase:p2",       "color": "#6366F1", "description": "P2 phase issue"},
    {"name": "implementation", "color": "#3B82F6", "description": "Implementation issue"},
    {"name": "acceptance",     "color": "#F59E0B", "description": "Acceptance issue"},
    {"name": "dry-run",        "color": "#94A3B8", "description": "Dry-run only, no real execution"},
    {"name": "no-real-factory","color": "#EF4444", "description": "Real Factory dispatch forbidden"},
    {"name": "no-github-push", "color": "#EF4444", "description": "GitHub push forbidden"},
    {"name": "no-linear-mutation","color":"#EF4444","description":"Linear state/label mutation forbidden"},
    {"name": "audit-required", "color": "#8B5CF6", "description": "Acceptance audit required"},
]

print("=== Step 1: Creating standard labels ===")
label_ids = {}
for lbl in LABELS_TO_CREATE:
    result = gql("""
        mutation CreateLabel($input: IssueLabelCreateInput!) {
            issueLabelCreate(input: $input) {
                success
                issueLabel { id name }
            }
        }
    """, {"input": {
        "name": lbl["name"],
        "color": lbl["color"],
        "description": lbl.get("description", ""),
        "teamId": TEAM_ID,
    }})
    if result and result.get("issueLabelCreate", {}).get("success"):
        label = result["issueLabelCreate"]["issueLabel"]
        label_ids[lbl["name"]] = label["id"]
        print(f"  Created: {lbl['name']} -> {label['id']}")
    else:
        # Label might already exist - try to find it
        print(f"  Label '{lbl['name']}' may already exist, querying...")
        team_result = gql("""
            query GetTeamLabels($teamId: String!) {
                team(id: $teamId) {
                    labels { nodes { id name } }
                }
            }
        """, {"teamId": TEAM_ID})
        if team_result:
            for node in team_result["team"]["labels"]["nodes"]:
                if node["name"] == lbl["name"]:
                    label_ids[lbl["name"]] = node["id"]
                    print(f"  Found existing: {lbl['name']} -> {node['id']}")
                    break
    time.sleep(0.3)

print(f"\n  Label IDs collected: {json.dumps(label_ids, indent=2)}")

# ── Step 2: Apply labels to issues ──────────────────────────────────
# Issue -> label mapping
IMPL_LABELS = ["phase:p2", "implementation", "dry-run", "no-real-factory", "no-github-push", "no-linear-mutation", "audit-required"]
AC_LABELS   = ["phase:p2", "acceptance", "dry-run", "no-real-factory", "no-github-push", "no-linear-mutation", "audit-required"]

ISSUE_LABEL_MAP = {
    # Implementation issues
    "743ead56-5c47-4a9a-b773-133064e50405": IMPL_LABELS,  # JTO-197 P2-01
    "e0bdf4af-cb41-4f67-81f6-1cf1d3c50507": IMPL_LABELS,  # JTO-198 P2-02
    "f4e93e32-f9f2-483e-a79e-3e92aa017211": IMPL_LABELS,  # JTO-199 P2-03
    "3a5adb3b-2c1f-42d5-819b-78ea937bf865": IMPL_LABELS,  # JTO-200 P2-04
    "7f17e6b8-de45-47a0-849a-1141507e10aa": IMPL_LABELS,  # JTO-201 P2-05
    "2d6d18eb-4647-4938-bf99-c4d5e78fec00": IMPL_LABELS,  # JTO-202 P2-06
    "f45b2a1a-8917-49e0-ac1a-d10ab0e0f94d": IMPL_LABELS,  # JTO-203 P2-07
    "2ebf731c-ce1b-4de0-992b-378c08048b80": IMPL_LABELS,  # JTO-204 P2-08
    # Acceptance issues
    "a552d579-0eb7-4866-bf4f-3fa8dd7a8ea2": AC_LABELS,    # JTO-205 P2-AC-01
    "9d8b8f3c-de12-4912-a1f8-18a40ef3cbd9": AC_LABELS,    # JTO-206 P2-AC-02
    "884c1f57-e0ba-4136-8a87-f4747393a454": AC_LABELS,    # JTO-207 P2-AC-03
    "00bc6c86-0baa-43b5-8218-e54637251ff9": AC_LABELS,    # JTO-208 P2-AC-04
    "6c09d494-5a77-4483-bc4d-3250d146ada4": AC_LABELS,    # JTO-209 P2-AC-05
    "7c4ace4a-4029-4805-9b15-c00dc35d7363": AC_LABELS,    # JTO-210 P2-AC-06
    "cedb2f1d-f670-4039-8d1c-3208a018ef4c": AC_LABELS,    # JTO-211 P2-AC-07
    "6820be51-0bae-4a38-87d1-c7ba503de844": AC_LABELS,    # JTO-212 P2-AC-08
    "4814eb35-0f59-41e4-800a-6c8ce2c36225": AC_LABELS,    # JTO-213 P2-AC-09
}

print("\n=== Step 2: Applying labels to issues ===")
for issue_id, label_names in ISSUE_LABEL_MAP.items():
    label_id_list = [label_ids[n] for n in label_names if n in label_ids]
    if not label_id_list:
        print(f"  SKIP {issue_id}: no label IDs resolved")
        continue

    result = gql("""
        mutation UpdateIssueLabels($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue { id identifier labels { nodes { id name } } }
            }
        }
    """, {"id": issue_id, "input": {"labelIds": label_id_list}})

    if result and result.get("issueUpdate", {}).get("success"):
        issue = result["issueUpdate"]["issue"]
        applied = [l["name"] for l in issue["labels"]["nodes"]]
        print(f"  {issue['identifier']}: {applied}")
    else:
        print(f"  FAILED {issue_id}")
    time.sleep(0.4)

# ── Step 3: Update project description/overview ─────────────────────
PROJECT_DESCRIPTION = """## 目标
定义 Factory 长任务 (long-task) dry-run 的完整规划，包括契约、子代理执行策略、GitLab CI 集成、真实 dispatch gate、Linear mutation gate、持久化审计升级、以及 tabletop 演练场景。

## 范围
- P2-01: 长任务 dry-run 契约定义 (✅ 已完成)
- P2-02: 子代理 checkpoint/runlog/heartbeat 策略
- P2-03: GitLab pipeline result provider contract
- P2-04: GitLab CI result → Linear dry-run comment flow
- P2-05: Factory real-dispatch gate 设计
- P2-06: Linear issueUpdate/label mutation dry-run gate
- P2-07: 持久化审计升级路径
- P2-08: Tabletop dry-run 演练场景

## 非范围
- 不执行真实 Factory dispatch
- 不推 GitHub
- 不修改 Linear issue 状态或标签
- 不创建 production webhook
- 不创建 APISIX route
- 不修改生产代码

## 阶段划分
- Phase A (基础契约): P2-01 → P2-AC-01
- Phase B (执行策略): P2-02 → P2-AC-02
- Phase C (GitLab 集成): P2-03, P2-04 → P2-AC-03, P2-AC-04
- Phase D (Gate 设计): P2-05, P2-06 → P2-AC-05, P2-AC-06
- Phase E (审计升级): P2-07 → P2-AC-07
- Phase F (集成验证): P2-08 → P2-AC-08
- Phase G (汇总验收): P2-AC-09

## 执行顺序
P2-01 → P2-AC-01 → P2-02 → P2-AC-02 → P2-03 → P2-AC-03 → P2-04 → P2-AC-04 → P2-05 → P2-AC-05 → P2-06 → P2-AC-06 → P2-07 → P2-AC-07 → P2-08 → P2-AC-08 → P2-AC-09

## 验收规则
- 每个 implementation issue 必须有独立 acceptance issue
- implementation 子代理不得自我验收
- 验收结论: PASS / CONDITIONAL PASS / BLOCKED
- 验收由独立 acceptance 子代理执行

## 禁止事项
- FORBID: 真实 Factory dispatch
- FORBID: GitHub push
- FORBID: Linear issue 状态变更
- FORBID: Linear label 变更
- FORBID: 创建 production webhook
- FORBID: 创建 APISIX route
- FORBID: 输出 secret/token/password
- FORBID: 配置 FACTORY_API_KEY

## 完成定义
- 所有 8 个 implementation issues 有交付物
- 所有 9 个 acceptance issues 验收 PASS
- 无真实 Factory dispatch
- 无 GitHub push
- 无 Linear 状态/标签变更
- Secret scan = 0 findings
- 输出 P2 planning closure report"""

print("\n=== Step 3: Updating project description ===")
# Try with short description first to test field availability
SHORT_DESC = "P2 planning phase: long-task dry-run contract, subagent policy, GitLab CI integration, dispatch gate. Dry-run only, no real execution."
result = gql("""
    mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
        projectUpdate(id: $id, input: $input) {
            success
            project { id name description }
        }
    }
""", {"id": PROJECT_ID, "input": {"description": SHORT_DESC}})

if result and result.get("projectUpdate", {}).get("success"):
    print(f"  Project description updated ({len(PROJECT_DESCRIPTION)} chars)")
else:
    print("  FAILED to update project description")

# ── Step 4: Update project content (overview in markdown) ───────────
PROJECT_CONTENT = """# P2 — Long-task dry-run + GitLab CI feedback loop

## 当前进度
- P2-01 (JTO-197): ✅ 已完成 implementation, 待 P2-AC-01 验收
- P2-02 ~ P2-08: 待执行
- P2-AC-01 ~ P2-AC-09: 待验收

## 下一步
**P2-AC-01 (JTO-205)**: 验收 P2-01 交付物

## 约束
- 所有任务 dry-run only
- 真实 Factory dispatch FORBIDDEN
- GitHub push FORBIDDEN
- Linear 状态/标签变更 FORBIDDEN"""

print("\n=== Step 4: Updating project content ===")
result = gql("""
    mutation UpdateProjectContent($id: String!, $input: ProjectUpdateInput!) {
        projectUpdate(id: $id, input: $input) {
            success
            project { id name }
        }
    }
""", {"id": PROJECT_ID, "input": {"content": PROJECT_CONTENT}})

if result and result.get("projectUpdate", {}).get("success"):
    print(f"  Project content updated ({len(PROJECT_CONTENT)} chars)")
else:
    print("  FAILED to update project content")

print("\n=== Standardization complete ===")
