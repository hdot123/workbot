# Linear + Factory + GitLab CI 闭环建设 — P0 准入阻断处理报告

> 审计日期: 2026-05-07
> 审计范围: P0 准入阻断处理 + GitLab 基础设施证据补齐 + YAML 扩展建议 + Factory 边界确认
> 审计模式: 只读，零改动
> 前置报告: linear-factory-gitlab-closure-readiness-audit-addendum.md

---

## 0. 总体结论

### **CONDITIONAL READY for dry-run design ONLY**

| 维度 | 判定 | 说明 |
|------|------|------|
| 是否允许进入最小 dry-run 闭环建设 | **YES** | 限定 dry-run 设计，不触发真实执行 |
| 是否禁止真实 Factory dispatch | **YES — 禁止** | FACTORY_API_KEY 不存在，GitLab CI 未 ready |
| 是否禁止 Linear 状态/标签变更 | **YES — 禁止** | 仅允许 commentCreate |
| 是否禁止 GitHub 直推 | **YES — 禁止** | memory-core-auto-sync-deploy.yml 含无 gate push，需先修复 |
| 是否允许 dry-run dispatch | **YES** | 当前已是 dry-run only |

---

## 1. Task 1: GitHub 直推路径风险处理

### 文件: `.github/workflows/memory-core-auto-sync-deploy.yml`

SHA256: `cc60f6757bdd374d1360d7cb37cc08f0b1bf3817965500081847c6093859f88b`

### 1.1 审计结果

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | 文件路径 | `.github/workflows/memory-core-auto-sync-deploy.yml` |
| 2 | 触发条件 | `repository_dispatch` (memory_release_published) + `workflow_dispatch` + `schedule` (cron: `17 */6 * * *`，即每 6 小时自动执行) |
| 3 | 是否存在 `git push origin HEAD:main` | **YES — 两处**：(1) Step "Commit and push auto-upgrade" (line ~136)；(2) Step "Auto-rollback on deploy failure" (line ~161) |
| 4 | 是否存在 GitLab CI pass gate | **NO** — 无任何 GitLab pipeline 验证 |
| 5 | 是否存在 manual approval | **NO** — 无 `environment: protection_rules`，无 `approval`，schedule 自动触发 |
| 6 | 是否可能被自动触发 | **YES** — `schedule: cron: "17 */6 * * *"` 每 6 小时自动触发 |
| 7 | 是否含 secret | **NO** — 仅使用 `${{ github.token }}`（GitHub Actions OIDC token），无硬编码 secret |

### 1.2 判定

```
BLOCKED — 无 gate GitHub push 路径存在
```

**风险等级: HIGH**

- 每 6 小时自动触发
- 无 GitLab CI pass 验证
- 无 manual approval
- 直接 push 到 `main` 分支
- 回滚操作也直接 push 到 `main`
- 违反 T10-PushGate 模板的所有硬规则 (H1-H6)

### 1.3 最小修复方案 (Patch Plan)

**原则: 本方案仅输出计划，不执行修改。**

```
--- memory-core-auto-sync-deploy.yml (current)
+++ memory-core-auto-sync-deploy.yml (proposed)

变更 1: 添加 gate job
+   gate-check:
+     runs-on: ubuntu-latest
+     outputs:
+       gitlab_ci_passed: ${{ steps.verify.outputs.passed }}
+     steps:
+       - name: Verify GitLab CI pass
+         id: verify
+         run: |
+           # GitLab CI verification gate
+           # Until GitLab CI is ready, this gate MUST fail closed
+           echo "passed=false" >> "$GITHUB_OUTPUT"
+           echo "BLOCKED: GitLab CI gate not yet configured"
+           exit 1

变更 2: sync-verify-deploy job 依赖 gate
    jobs:
+   gate-check:
+     ...
      sync-verify-deploy:
        runs-on: ubuntu-latest
+       needs: gate-check
+       if: ${{ needs.gate-check.outputs.gitlab_ci_passed == 'true' }}
        ...

变更 3: 禁用 schedule 触发（直到 gate ready）
    on:
-     schedule:
-       - cron: "17 */6 * * *"
+     # schedule disabled until GitLab CI gate is ready
+     # schedule:
+     #   - cron: "17 */6 * * *"

变更 4: 在 push 步骤前添加 T10-PushGate 验证
      - name: T10-PushGate verification
+       run: |
+         echo "ERROR: Direct GitHub push is blocked by P0 gate"
+         echo "Required: pipeline_id, pipeline_status=success, commit_sha match"
+         echo "Current: no GitLab CI pipeline evidence"
+         exit 1
```

**修复效果:**

| 规则 | 修复前 | 修复后 |
|------|--------|--------|
| 禁止直接 push GitHub | 违反 | 遵守（gate fail-closed） |
| GitLab CI pass 后才 sync | 无 gate | gate-check 验证（当前 fail-closed） |
| 显式 gate | 无 | `gitlab_ci_passed` output |
| schedule 自动触发 | 每 6h | 禁用 |
| fail-closed | 否 | 是 |

---

## 2. Task 2: GitLab 基础设施证据补齐

### 结论: **BLOCKED — 无可验证的 GitLab 实例**

### 2.1 证据全表

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 2.1 | GitLab 实例 URL | **未发现** | 仓库仅引用 `gitlab.example.com`（设计文档中的占位符），无真实 URL。Git remote 仅 `github.com/hdot123/workbot.git` |
| 2.2 | 是否可访问 | **无法验证** | 无 URL |
| 2.3 | gateway-admin 项目 | **不在 GitLab** | `gateway-admin` 仅出现在 AEdu k8s deployment 文档中（`kubectl set env deployment/gateway-admin`），是 k8s 部署名，非 GitLab 项目 |
| 2.4 | webhook-ingress 项目 | **不在 GitLab** | 仅有 GitHub remote |
| 2.5 | factory-adapter 项目 | **不在 GitLab** | 仅为 Python 模块 `workspace/tools/webhook_ingress/factory_adapter.py` |
| 2.6 | infra/gitlab-ci-standards | **不存在** | 无此目录或文件 |
| 2.7 | runner 是否存在 | **无证据** | 无 runner token、无 `.gitlab-ci.yml` |
| 2.8 | runner 是否 online | **无法验证** | 同上 |
| 2.9 | runner tags / executor | **无法验证** | 同上 |
| 2.10 | 历史 pipeline | **无证据** | 仓库无 `.gitlab-ci.yml` |
| 2.11 | 标准 `.gitlab-ci.yml` 模板 | **不存在** | 无任何 GitLab CI 文件 |
| 2.12 | secret scan / test / e2e job | **仅 GitHub Actions** | `webhook-ingress-validation.yml` (34 tests passed) |
| 2.13 | GitLab webhook 能力 | **设计文档中描述** | `2026-05-03-gitlab-webhook-n8n-unified-architecture.md` 定义了 GitLab webhook 接入方案，但纯设计，无实现 |
| 2.14 | `gateway-admin` 的实际身份 | **k8s deployment** | `kubectl set env deployment/gateway-admin -n aedu`，是 AEdu 项目的 k8s 服务，不是 GitLab 项目 |

### 2.2 GitLab 架构设计文档中引用的占位 URL

```
GITLAB_BASE_URL=https://gitlab.example.com     ← 占位符
git@gitlab.example.com:group/repo.git          ← 占位符
https://gitlab.example.com/group/repo/...       ← 占位符
```

所有 GitLab URL 均为 `gitlab.example.com`，是 RFC 2606 保留域名，不是真实实例。

### 2.3 结论

```
GitLab infra: BLOCKED
BLOCKED_REASON: 无真实 GitLab 实例 URL、无项目、无 runner、无 pipeline。
所有 GitLab 引用均为设计文档中的占位符 (gitlab.example.com)。
需要用户确认: 是否已部署 GitLab 实例，或是否计划部署。
```

---

## 3. Task 3: YAML baseline 最小扩展建议

**仅建议，不修改文件。**

### 3.1 当前 baseline

| 文件 | SHA256 | 状态 |
|------|--------|------|
| routes.yaml | `0801a081...a2fc1f` | Linear + Factory enabled；GitHub/Slack/PostHog/PagerDuty/UptimeKuma disabled；**GitLab 缺失** |
| canonical-webhook-event-v1.json | `51d9d2ba...9925f` | provider enum 7 值；canonical_type 22 值；**均无 gitlab** |
| server.py | `b8443515...2595a` | 2 endpoint (/webhooks/linear, /webhooks/factory) |
| factory_adapter.py | `55ffed15...2e33d` | Factory HMAC-SHA256 验证 |
| lifecycle.py | `97ff030e...994d` | 5 state 内存 state machine |
| actions.py | `baa1b15e...224e` | 2 action (canary comment + dispatch dry-run) |
| dispatch_payload.py | `6db3942d...22bc` | main-thread + subagent + CI policy |

### 3.2 最小扩展计划

#### 扩展 1: routes.yaml — 添加 gitlab provider

```yaml
# 新增（disabled，dry-run only）
  gitlab:
    enabled: false                                    # 不启用
    ingress_path: /webhooks/gitlab
    webhook_secret_env: WEBHOOK_SECRET_GITLAB
    n8n_webhook_url: http://127.0.0.1:5678/webhook/canonical-events
    routes:
      - match:
          canonical_type: push
          canonical_action: created
        n8n_webhook_url: http://127.0.0.1:5678/webhook/gitlab-push
      - match:
          canonical_type: merge_request
          canonical_action: updated
        n8n_webhook_url: http://127.0.0.1:5678/webhook/gitlab-mr-events
      - match:
          canonical_type: pipeline
          canonical_action: updated
        n8n_webhook_url: http://127.0.0.1:5678/webhook/gitlab-pipeline-events
```

**约束: enabled=false，不创建 route，不创建 webhook。**

#### 扩展 2: canonical-webhook-event-v1.json — 添加 gitlab

```json
"provider": { "enum": [..., "gitlab"] }

"canonical_type": { "enum": [..., "merge_request", "pipeline", "job", "tag_push", "note"] }
```

#### 扩展 3: 新建 gitlab_adapter.py

- GitLab webhook token 验证（`X-Gitlab-Token`）
- Payload normalize to canonical event v1
- 支持 `Push Hook`, `Merge Request Hook`, `Pipeline Hook`, `Job Hook`

#### 扩展 4: drift-check 覆盖

| 检查项 | 需新增 |
|--------|--------|
| APISIX route drift | 当前已覆盖（routes.yaml ingress_path） |
| nginx config drift | 需新增声明式检查 |
| Cloudflare URL drift | 需新增声明式检查 |
| GitLab route/provider drift | 需新增（gitlab provider 添加后） |
| Linear route/provider drift | 当前隐含覆盖，需声明式 |

#### 扩展 5: rollback-policy 覆盖

| 场景 | 当前 | 需新增 |
|------|------|--------|
| Linear provider rollback | 代码回滚 | 声明式 rollback plan |
| GitLab provider rollback | 无 | 需新增 |
| Factory lifecycle rollback | 内存丢失 | 需持久化 + rollback |

### 3.3 所有扩展项必须遵守

| 规则 | 要求 |
|------|------|
| dry-run first | 所有新增项先以 disabled/false 状态添加 |
| 不启用 provider | `enabled: false` |
| 不创建 route | 仅声明 ingress_path |
| 不创建 webhook | 无 n8n workflow 调用 |
| validation 绑定 delivery_id/request_id/event_id | 已有，保持 |

---

## 4. Task 4: Factory dispatch 边界确认

### 结论: **DRY_RUN_ONLY**

### 4.1 审计全表

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 4.1 | 当前是否只有 dry-run dispatch payload | **YES** | `dispatch_payload.py` 中 `dispatch_mode=dry_run`，`FactoryDispatchDryRunExecutor` 仅构建 payload 不调用 API |
| 4.2 | 是否存在真实 Factory API endpoint 配置 | **NO** | 代码中无 `api.factory.ai` 调用，无 `droid exec` 命令构建 |
| 4.3 | 是否存在 FACTORY_API_KEY env | **NO** | 仓库无此环境变量引用 |
| 4.4 | Factory 官方文档是否支持出站 webhook | **未确认** | Factory llms.txt 和各文档页面未描述 outbound webhook 能力。集成模式是 Factory 主动拉取（OAuth Linear），非推送 |
| 4.5 | Stop/SubagentStop hook 作为 fallback | **可用** | Factory 官方支持 Stop/SubagentStop hooks，可在 session 完成时执行 shell 命令（如 curl 回调）。但不应作为主事件总线 |
| 4.6 | Factory Linear 集成作为替代闭环 | **可用** | Factory 官方支持 Linear OAuth 集成，可直接更新 issue 状态/评论 |
| 4.7 | 当前是否允许真实 dispatch | **NO** | 无 FACTORY_API_KEY、无 droid exec 调用、无 autonomy level 设计 |

### 4.2 Factory dispatch 判定

```
Factory dispatch: DRY_RUN_ONLY
是否允许真实 dispatch: NO（需 FACTORY_API_KEY + GitLab CI gate + autonomy level 设计）
是否允许最小 dry-run: YES
```

### 4.3 Factory 闭环路径评估

| 路径 | 角色 | 可行性 | 说明 |
|------|------|--------|------|
| Factory Stop hook -> curl /webhooks/factory | 回调通知 | **HIGH** | 官方支持 hook，但非主事件总线，仅作补充 |
| Factory Linear OAuth 集成 | 状态回写 | **HIGH** | 官方原生支持，Factory 完成后可直接更新 Linear issue |
| `droid exec` headless + JSON output | 任务执行 | **HIGH** | 官方支持，需 FACTORY_API_KEY |
| Factory 出站 webhook | 事件推送 | **未确认** | 官方文档无此描述 |

### 4.4 真实 dispatch 安全前置条件

| # | 前置条件 | 当前状态 |
|---|----------|----------|
| 1 | FACTORY_API_KEY 配置 | **缺失** |
| 2 | GitLab CI pipeline 门禁 | **缺失** |
| 3 | autonomy level 设计 | **缺失** |
| 4 | max_fix_attempts loop guard | 设计完成（dispatch_payload.py 中 max=3） |
| 5 | Factory -> Linear 回写验证 | **未实现** |
| 6 | Factory run 状态持久化 | **未实现**（纯内存） |

---

## 5. P0 修复清单

| # | 问题 | 修复 | 优先级 | 阻断级别 |
|---|------|------|--------|----------|
| P0-1 | memory-core-auto-sync-deploy.yml 无 gate push | 添加 gate-check job（fail-closed）+ 禁用 schedule | **P0** | 阻断真实闭环 |
| P0-2 | GitLab 实例不存在 | 用户确认：是否部署 | **P0** | 阻断 CI 门禁 |
| P0-3 | canonical schema 无 gitlab | 添加 gitlab enum（disabled） | **P0** | 阻断 GitLab adapter |
| P0-4 | routes.yaml 无 gitlab provider | 添加 gitlab provider（disabled） | **P0** | 阻断 GitLab 路由 |

### P0 修复依赖顺序

```
P0-2 (GitLab 确认) 
  → P0-1 (push gate 加固)
  → P0-3 (schema 扩展)
  → P0-4 (routes 扩展)
```

---

## 6. 是否允许进入最小 dry-run 闭环建设

### **YES — CONDITIONAL**

允许范围（与上一轮一致，增加 push gate 修复要求）:

| 允许 | 不允许 |
|------|--------|
| Factory dry-run dispatch payload 构建 | 真实 Factory API 调用 |
| Linear canary comment (commentCreate) | Linear issueUpdate / labelCreate |
| webhook-ingress canonical event 存储 | GitLab CI pipeline 触发 |
| canonical schema / routes.yaml 扩展设计 (disabled) | 启用任何新 provider |
| GitLabAdapter 代码开发 (disabled) | 推送任何变更到 GitHub main |
| Factory Stop hook 设计 | 绕过 webhook-ingress 直接操作 |

**新增要求**: 在任何代码变更被推送到 GitHub 前，P0-1 (push gate) 必须先修复。

---

## 7. Secret Scan Findings

| 范围 | Findings |
|------|----------|
| `.github/workflows/*.yml` | **0** |
| `workspace/tools/webhook_ingress/*.py` | **0** |
| `workspace/tools/webhook_ingress/*.yaml` | **0** |
| `workspace/tools/webhook_ingress/*.json` | **0** |
| `docs/webhook-ingress/*.md` | **0** |
| 全仓库 (FACTORY_API_KEY / fk- / lin_api_) | **0** |
| **总计** | **0** |

---

## 8. 相关文件路径和 SHA256

### GitHub Workflows

| 文件 | SHA256 |
|------|--------|
| `.github/workflows/memory-core-auto-sync-deploy.yml` | `cc60f6757bdd374d1360d7cb37cc08f0b1bf3817965500081847c6093859f88b` |
| `.github/workflows/memory-hook-external-core-only.yml` | `3dc14b68648b7766bf57abfd238a21802431f0ddc54e52f8f4dbaa0748581400` |
| `.github/workflows/webhook-ingress-validation.yml` | `aeaf937792f971369ca92e5e17af120ee5c8cc4c268bc50273cff6a454b7058a` |

### Webhook Ingress Core

| 文件 | SHA256 |
|------|--------|
| `workspace/tools/webhook_ingress/routes.yaml` | `0801a081752001b40c8fa93e641b9fc0341a6527082c894945436ecfc6a2fc1f` |
| `workspace/tools/webhook_ingress/schemas/canonical-webhook-event-v1.json` | `51d9d2ba2871fe838265f92d3fb066f4a349fb1862c0fb8017510601aa19925f` |
| `workspace/tools/webhook_ingress/server.py` | `b8443515d928145fa09f7a0b6b2794152783c85b17ee2aaa9f7a7dc89402595a` |
| `workspace/tools/webhook_ingress/factory_adapter.py` | `55ffed157b105070b591bd7a3bb8b946729e1cb8a03851a273eb261510c2e33d` |
| `workspace/tools/webhook_ingress/lifecycle.py` | `97ff030e75d5e159df7cea54884acd76895c79980ae563a603e6b60d5f9b994d` |
| `workspace/tools/webhook_ingress/actions.py` | `baa1b15e065d372932cebd429c57ce86fd1855673ba13b98c18953fa9b59224e` |
| `workspace/tools/webhook_ingress/dispatch_payload.py` | `6db3942d0f952528761ead9fde08ec5d32d6f80fe19abc040156663ba39822bc` |
| `workspace/tools/webhook_ingress/ingress.py` | `a1afd33dfab931a7931ea7fc31184c3b1405ae8dec09a637065fe97db4936ef7` |
| `workspace/tools/webhook_ingress/adapter.py` | `cff59539bd8eeaa39f9a1a8002e16aae1dab05e81a35ace36552b2aa3af5c95d` |
| `workspace/tools/webhook_ingress/redaction.py` | `5738010afd4a33d369998ebcdcaabc076197611a3e829787e812c3543e2975aa` |
| `workspace/tools/webhook_ingress/schema.py` | `5f4b4f8f8c7430919e1fd60b11c025f2fcba546c603548ccf3cebfe727b2c4c8` |
| `workspace/tools/webhook_ingress/routes.py` | `fbc568dbefadbae7b7a140963628cfc832f91e10c16518e4cd31b638c283560c` |

---

## 9. 最终判定规则校验

| 规则 | 判定 | 说明 |
|------|------|------|
| 无 gate GitHub push → BLOCKED for real closure | **CONFIRMED BLOCKED** | P0-1 需修复后才允许任何 push |
| GitLab infra 不可验证 → 不得真实 dispatch | **PASS** | 不执行真实 dispatch |
| Factory API 能力不明 → 不得真实 dispatch | **PASS** | 不执行真实 dispatch |
| secret scan findings > 0 → BLOCKED | **PASS** | 0 findings |
| 不改 Linear 状态/不推 GitHub/不绕过 CI → 允许 dry-run | **PASS** | 所有活动均为 dry-run 设计 |

---

## 10. 下一阶段最小任务边界

```
阶段 0 (P0 修复 — 必须在一切之前):
  → 用户确认 GitLab 实例是否存在 (P0-2)
  → 修复 memory-core-auto-sync-deploy.yml push gate (P0-1)
  → canonical schema 添加 gitlab enum [disabled] (P0-3)
  → routes.yaml 添加 gitlab provider [disabled] (P0-4)

阶段 1 (dry-run 设计):
  → gitlab_adapter.py 开发 [disabled]
  → Factory Stop hook 回调设计
  → Factory lifecycle 持久化设计
  → Linear issueUpdate dry-run mutation 设计

阶段 2 (需要 GitLab 实例就绪):
  → .gitlab-ci.yml 定义
  → GitLab runner 配置
  → GitLab webhook 入站启用
  → 真实 Factory dispatch (需要 FACTORY_API_KEY + GitLab CI gate)
```

---

*审计报告结束*
