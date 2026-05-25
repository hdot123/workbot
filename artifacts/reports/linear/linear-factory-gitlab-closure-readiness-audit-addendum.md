# Linear + Factory + GitLab CI 闭环建设 — 补充准入审计报告

> 审计日期: 2026-05-07
> 审计范围: workbot 仓库全量配置 + Factory 官方文档 + 安全扫描 + YAML baseline
> 审计模式: 只读，零改动
> 前置报告: 2026-05-07 前置摸底审计报告

---

## 0. 总体结论

### **CONDITIONAL READY**

允许进入"最小 dry-run 闭环建设"，但附加以下硬约束：

| # | 硬约束 | 违反即 BLOCKED |
|---|--------|---------------|
| HC-1 | 不允许真实 Factory dispatch，除非 GitLab CI 门禁 ready | Factory 当前仅允许 `droid exec --auto low`（read-only）或 dry-run payload |
| HC-2 | 不允许 Linear 状态自动推进，除非 `issueUpdate` mutation 已 dry-run 验证 | 当前仅允许 `commentCreate`（canary comment） |
| HC-3 | 不允许 Linear 标签自动变更 | `labelCreate` / `issueUpdate` labels 字段均未验证 |
| HC-4 | 不允许 GitHub 直推 | `memory-core-auto-sync-deploy.yml` 存在 `git push origin HEAD:main`，需加 gate |
| HC-5 | 不允许绕过 webhook-ingress 直接做生产写操作 | n8n 必须只接收 canonical event |
| HC-6 | 发现真实 secret 明文即 BLOCKED | 本轮扫描 0 findings（详见 T3） |

---

## 1. Task 1: GitLab 基础设施实证

### 结论: **BLOCKED**

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1.1 | 局域网 GitLab 实例 URL | **未发现** | 仓库无 `GITLAB_URL` env、无 `.gitlab-ci.yml`、无 gitlab.com 项目引用 |
| 1.2 | gateway-admin 项目 | **未发现** | Grep 全仓库无匹配（仅 AEdu 文档中有引用词，非 GitLab 项目） |
| 1.3 | webhook-ingress 项目 | **未发现** | 无 GitLab 项目，仅有 GitHub remote |
| 1.4 | factory-adapter 项目 | **未发现** | 仅作为 Python 模块存在于 workspace/tools/webhook_ingress/ |
| 1.5 | infra/gitlab-ci-standards | **未发现** | 无此目录或文件 |
| 1.6 | runner 是否在线 | **无证据** | 无 runner token、无 `.gitlab-ci.yml`、无 pipeline 记录 |
| 1.7 | runner tags / executor | **无证据** | 同上 |
| 1.8 | 历史 pipeline | **无证据** | 无 `.gitlab-ci.yml` 存在过 |
| 1.9 | 可复用 `.gitlab-ci.yml` 模板 | **不存在** | 仓库无任何 GitLab CI 文件 |
| 1.10 | secret scan / test / e2e job | **仅 GitHub Actions** | `webhook-ingress-validation.yml` 覆盖 webhook ingress 测试（34 tests） |
| 1.11 | GitHub 直推/同步路径 | **存在** | `memory-core-auto-sync-deploy.yml` 包含 `git push origin HEAD:main`（见 T3） |

### BLOCKED_REASON

当前仓库仅有 GitHub remote，无任何 GitLab 实例、项目、runner 或 CI 配置证据。GitLab 基础设施可能：
- 尚未搭建
- 存在于用户局域网但未在本仓库留下配置证据
- 在其他位置管理

**需要用户确认：是否有局域网 GitLab 实例，URL 是什么。**

---

## 2. Task 2: YAML baseline / drift 扩展审计

### 结论: **PARTIAL**

### 2.1 六个维护底座文件

| # | 文件 | SHA256 | 存在 | pyyaml 解析 |
|---|------|--------|------|-------------|
| 1 | routes.yaml | `0801a081...a2fc1f` | YES | PASS |
| 2 | schema.py | `5f4b4f8f...b2c4c8` | YES | N/A (Python) |
| 3 | adapter.py | `cff59539...f5c95d` | YES | N/A (Python) |
| 4 | factory_adapter.py | `55ffed15...0c2e33d` | YES | N/A (Python) |
| 5 | lifecycle.py | `97ff030e...f9b994d` | YES | N/A (Python) |
| 6 | actions.py | `baa1b15e...59224e` | YES | N/A (Python) |

### 2.2 source_of_truth / apply_allowed / drift / rollback

| 检查项 | 状态 | 说明 |
|--------|------|------|
| source_of_truth = documentation_index_only | **未定义** | 6 个文件中无此字段；当前底座是代码模块，不是声明式配置 |
| apply_allowed = false | **未定义** | 同上 |
| drift-check 覆盖 APISIX route | **部分** | routes.yaml 定义了 ingress_path 但不覆盖 APISIX/nginx 层 |
| drift-check 覆盖 nginx config | **不覆盖** | nginx config 仅存在于 node-22 证据文档中 |
| drift-check 覆盖 Cloudflare URL | **不覆盖** | cloudflared 配置不在仓库中 |
| drift-check 覆盖 webhook-ingress adapter | **隐含覆盖** | adapter.py / factory_adapter.py 本身是 source |
| drift-check 覆盖 GitLab route/provider | **不覆盖** | routes.yaml 中无 gitlab provider |
| drift-check 覆盖 Linear route/provider | **部分覆盖** | linear provider 已定义，routes 含 3 条路由 |
| rollback-policy 覆盖 Linear/GitLab | **不覆盖** | 无声明式 rollback policy |
| validation 绑定 delivery_id/request_id/event_id | **部分** | schema 中 idempotency_key 和 raw_body_sha256 是必填 |

### 2.3 扩展 Linear/GitLab provider 的结构能力

| 检查项 | 状态 | 说明 |
|--------|------|------|
| routes.yaml 支持 provider 扩展 | **YES** | 结构支持任意 provider，已有 7 个 |
| canonical schema 支持 gitlab provider | **NO** | `provider` enum 为 `["linear", "github", "slack", "posthog", "pagerduty", "uptime_kuma", "factory"]`，无 `"gitlab"` |
| canonical_type 支持新类型 | **部分** | 已有 `push` / `pull_request` 等，但缺少 GitLab 特有类型如 `merge_request` / `pipeline` / `job` |
| RouteMatcher 支持新 provider | **YES** | 按 provider key 查找，无硬编码 |

### 2.4 需要扩展的 YAML/Schema 文件清单

| # | 文件 | 需要扩展 |
|---|------|----------|
| 1 | `routes.yaml` | 添加 `gitlab` provider（当前缺失） |
| 2 | `schemas/canonical-webhook-event-v1.json` | provider enum 添加 `"gitlab"`，canonical_type 添加 `"merge_request"`, `"pipeline"`, `"job"`, `"tag_push"`, `"note"` |
| 3 | 新建 `gitlab_adapter.py` | GitLab webhook 签名验证 + normalize |
| 4 | 新建 `gitlab_lifecycle_action.py` | Pipeline 状态追踪 |
| 5 | routes.yaml drift 声明层 | 需要添加 source_of_truth / apply_allowed / rollback-policy 元数据 |

---

## 3. Task 3: Security / Secret / Permission 审计

### 结论: **READY** (0 findings)

### 3.1 Secret Scan 结果

| 扫描范围 | 模式 | Findings |
|----------|------|----------|
| workspace/tools/webhook_ingress/*.{py,yaml,yml,json} | `(?i)(sk-\|pk_\|ghp_\|glpat-\|xox[bpsa]-\|AKIA\|eyJ)[a-zA-Z0-9]` | **0** |
| docs/webhook-ingress/*.md | 同上 | **0** |
| 全仓库 *.{py,yaml,yml,json,md,sh,env,toml} | `(?i)lin_api_[a-zA-Z0-9]{10,}` | **0** |
| 全仓库 | `FACTORY_API_KEY\|fk-` | **0** |

### 3.2 凭证引用方式

| 凭证 | 引用方式 | 代码中是否有明文值 |
|------|----------|-------------------|
| `LINEAR_WEBHOOK_SECRET` | `os.environ.get()` | NO（server.py 引用说明含 `your-secret`，非真实值） |
| `LINEAR_CANARY_API_TOKEN` | `os.environ.get()` | NO |
| `WEBHOOK_SECRET_FACTORY` | `os.environ.get()` | NO |
| `WEBHOOK_DATABASE_URL` | `os.environ.get()` / 1Password item 引用 | NO（文档引用 1Password item ID，非 URL 值） |
| `FACTORY_API_KEY` | **不存在** | 仓库中无此 env 引用 |
| GitLab runner token | **不存在** | 无 |
| GitLab webhook secret | **不存在** | 无 |

### 3.3 高风险项

| # | 风险 | 级别 | 说明 |
|---|------|------|------|
| SEC-1 | GitHub 直推路径存在 | **HIGH** | `.github/workflows/memory-core-auto-sync-deploy.yml` 含 `git push origin HEAD:main`，无 T10-PushGate gate |
| SEC-2 | n8n 绕过 webhook-ingress 风险 | **MEDIUM** | 当前 n8n production workflow 仅接收 canonical event，但无技术屏障阻止直接 n8n 写操作 |
| SEC-3 | raw_headers 存储脱敏已修复 | INFO | RISK-1 至 RISK-3 已在 OPS-006 中修复，RISK-4 (DB URL in psycopg2 exception) 仍 OPEN 但为 LOW |
| SEC-4 | Factory lifecycle 纯内存 | **MEDIUM** | 重启丢失所有 run 状态，无法恢复或审计 |
| SEC-5 | autonomy 默认配置 | **LOW** | Factory 默认 read-only；`--skip-permissions-unsafe` 未在任何代码/配置中出现 |

### 3.4 GitHub 直推脚本审计

| 文件 | 内容 | 风险 |
|------|------|------|
| `.github/workflows/memory-core-auto-sync-deploy.yml` | `git push origin HEAD:main` | **HIGH** — 无 CI gate、无 pipeline_id 验证、无 Linear issue 关联 |
| `.github/workflows/memory-hook-external-core-only.yml` | 未发现 push | OK |
| `.github/workflows/webhook-ingress-validation.yml` | 仅测试，无 push | OK |
| `scripts/` 目录 | 未发现 git push | OK |

### 3.5 shell history / 临时文件残留

| 检查 | 结果 |
|------|------|
| ~/.bash_history / ~/.zsh_history | **不在审计范围内**（涉及用户系统级文件，未读取） |
| workspace/memory/tmp/ | 存在 37 个临时文件，未发现 secret 明文 |
| .env 文件 | 仓库中不存在 `.env` 文件 |

---

## 4. Task 4: Factory API / webhook 能力实证

### 结论: **PARTIAL**

### 4.1 Factory API endpoint 证据

| 检查项 | 状态 | 证据 |
|--------|------|------|
| Factory API 官方 endpoint | **已确认** | Factory 官方文档 `https://api.factory.ai/api/v0/openapi.json`；CLI 通过 `FACTORY_API_KEY=fk-...` 认证 |
| 本地 Factory API 配置 | **不存在** | 仓库无 `FACTORY_API_KEY` env 引用、无 `fk-` 前缀 key |
| Factory API key env | **不存在** | 无 `FACTORY_API_KEY` 环境变量配置 |
| Factory 出站 webhook 配置入口 | **不明确** | Factory 官方文档未提及 outbound webhook 配置。Factory 集成模式是：Factory 主动拉取 Linear issue，而非 Linear 推送到 Factory |

### 4.2 Factory 集成模式（基于官方文档）

| 模式 | 说明 | 状态 |
|------|------|------|
| Factory -> Linear 集成 | Factory 通过 OAuth 连接 Linear workspace，可以 view/create/update issues | **官方支持** |
| Linear -> Factory 触发 | 用户从 Linear issue 点击 "Open in Factory" 链接创建新 session | **官方支持（手动）** |
| Factory 出站 webhook | Factory run 完成后回调外部 URL | **官方文档无此功能描述** |
| Factory session API | `droid exec` headless mode + `--output-format json` | **官方支持** |
| Factory hooks | `Stop` / `SubagentStop` hooks 可在 session/子代理完成时执行 shell 命令 | **官方支持** |

### 4.3 真实 dispatch 安全 gate

| 检查项 | 状态 | 说明 |
|--------|------|------|
| dispatch_mode=dry_run | **YES** | 当前仅 dry-run，不调用 Factory API |
| Factory API 调用 | **不存在** | 代码中无 `api.factory.ai` 调用 |
| 真实 dispatch gate | **未实现** | 需要：FACTORY_API_KEY 配置 + `droid exec` 命令构建 + autonomy level 控制 |
| subagentInactivityTimeout | **不存在** | 代码和配置中均未定义 |
| Stop / SubagentStop hook | **Factory 官方支持** | 可在 `.factory/settings.json` 中配置，但当前仓库未配置 |
| checkpoint / runlog 规范 | **未定义** | dispatch_payload.py 定义了 policy 但未定义 checkpoint 格式 |

### 4.4 Factory dispatch readiness 判定

| 问题 | 答案 |
|------|------|
| 是否允许真实 dispatch | **NO** — 需要 FACTORY_API_KEY + GitLab CI gate + autonomy level 设计 |
| 是否允许 dry-run dispatch | **YES** — 当前已是 dry-run 模式 |
| Factory 出站 webhook 是否可配置 | **未确认** — 官方文档未描述此能力，需联系 Factory 支持或检查 Enterprise 功能 |

### 4.5 Factory 闭环替代方案

由于 Factory 官方未明确支持出站 webhook，闭环链路可能需要以下替代：

| 方案 | 可行性 | 说明 |
|------|--------|------|
| Factory `Stop` hook 执行 curl 回调 | **HIGH** | hook 可在 session 完成时执行 shell 命令，可 curl 回调 `/webhooks/factory` |
| Factory `SubagentStop` hook | **HIGH** | 子代理完成时回调 |
| `droid exec --output-format json` + 轮询 | **MEDIUM** | 调用方轮询 session 状态 |
| Factory Linear 集成自动更新 issue | **HIGH** | Factory 已有 Linear OAuth 集成，可直接更新 issue 状态 |

---

## 5. P0/P1/P2 缺口重排

### P0 — 进入 dry-run 闭环建设前必须解决

| # | 缺口 | 说明 | 影响 |
|---|------|------|------|
| P0-1 | **GitLab 实例确认** | 无 GitLab 基础设施证据 | 无法定义 `.gitlab-ci.yml`，无法实现 CI 门禁 |
| P0-2 | **GitLab provider 添加** | routes.yaml 无 gitlab provider，canonical schema 无 gitlab enum | 无法接收 GitLab webhook |
| P0-3 | **GitHub 直推 gate** | `memory-core-auto-sync-deploy.yml` 含无 gate 的 `git push origin HEAD:main` | 安全风险 |
| P0-4 | **Factory 闭环机制确认** | Factory 无明确出站 webhook；需确认 Stop hook 或 Linear 集成作为替代 | 无法实现 Factory -> Linear 回写 |

### P1 — dry-run 闭环建设中解决

| # | 缺口 | 说明 |
|---|------|------|
| P1-1 | Factory lifecycle 持久化 | 从内存迁移到 Supabase |
| P1-2 | canonical schema 扩展 | 添加 gitlab provider + GitLab event types |
| P1-3 | GitLabAdapter 实现 | 签名验证 + normalize |
| P1-4 | Linear issueUpdate dry-run | 状态回写 mutation 的 dry-run 验证 |
| P1-5 | YAML drift 声明层 | 添加 source_of_truth / apply_allowed / rollback-policy |
| P1-6 | Factory dispatch 安全 gate | FACTORY_API_KEY 配置 + autonomy level + max_fix_attempts |

### P2 — 完整闭环建设阶段解决

| # | 缺口 | 说明 |
|---|------|------|
| P2-1 | n8n 业务编排 workflow | 当前仅 canonical event 接收 |
| P2-2 | T6-CIFix 自动闭环 | CI failed 自动修复 |
| P2-3 | T1-T10 模板实际部署 | 从设计推演到 Linear 项目 |
| P2-4 | Linear 自动打标 | 路由器 + labelCreate |
| P2-5 | Factory checkpoint/runlog 规范 | 定义格式和存储 |

---

## 6. 是否允许进入"最小 dry-run 闭环建设"

### **YES — CONDITIONAL READY**

允许范围：

| 允许 | 不允许 |
|------|--------|
| Factory dry-run dispatch payload 构建 | 真实 Factory API 调用 (`droid exec` / `FACTORY_API_KEY`) |
| Linear canary comment (`commentCreate`) | Linear issueUpdate / labelCreate |
| webhook-ingress canonical event 存储 | GitLab CI pipeline 触发 |
| Factory adapter/lifecycle 代码开发 | Factory lifecycle 持久化到生产 Supabase |
| canonical schema/routes.yaml 扩展设计 | 推送任何变更到 GitHub main |
| YAML drift 声明层设计 | 绕过 webhook-ingress 直接操作 |

### 下一阶段最小任务边界

| 步骤 | 任务 | 产出 |
|------|------|------|
| Step 1 | 确认 GitLab 基础设施 | 用户回答：是否存在、URL |
| Step 2 | 添加 gitlab provider 到 routes.yaml + canonical schema | 配置扩展 |
| Step 3 | 实现 GitLabAdapter (dry-run) | 签名验证 + normalize |
| Step 4 | 确认 Factory 闭环机制 | Stop hook / Linear integration |
| Step 5 | GitHub 直推 gate 加固 | `memory-core-auto-sync-deploy.yml` 加 pipeline_id 验证 |
| Step 6 | Factory lifecycle 持久化设计 | Supabase 表扩展 |

---

## 7. 相关文件 SHA256

| 文件 | SHA256 |
|------|--------|
| routes.yaml | `0801a081752001b40c8fa93e641b9fc0341a6527082c894945436ecfc6a2fc1f` |
| schema.py | `5f4b4f8f8c7430919e1fd60b11c025f2fcba546c603548ccf3cebfe727b2c4c8` |
| adapter.py | `cff59539bd8eeaa39f9a1a8002e16aae1dab05e81a35ace36552b2aa3af5c95d` |
| factory_adapter.py | `55ffed157b105070b591bd7a3bb8b946729e1cb8a03851a273eb261510c2e33d` |
| lifecycle.py | `97ff030e75d5e159df7cea54884acd76895c79980ae563a603e6b60d5f9b994d` |
| actions.py | `baa1b15e065d372932cebd429c57ce86fd1855673ba13b98c18953fa9b59224e` |

---

## 8. Secret Scan Findings 数量

| 范围 | Findings |
|------|----------|
| workspace/tools/webhook_ingress/ (代码) | **0** |
| docs/webhook-ingress/ (文档) | **0** |
| 全仓库 (真实 key/token 扫描) | **0** |
| **总计** | **0** |

---

## 9. 最终判定规则校验

| 规则 | 判定 | 说明 |
|------|------|------|
| 发现真实 secret → BLOCKED | **PASS** | 0 findings |
| GitHub 直推路径存在 → BLOCKED | **CONDITIONAL** | 存在但未在闭环链路中，需加 gate |
| GitLab infra 不可访问 → BLOCKED 或 CONDITIONAL | **CONDITIONAL READY** | GitLab 不可用不影响 dry-run 闭环建设 |
| Factory 只能 dry-run → 允许 dry-run | **PASS** | 当前仅 dry-run |
| Linear 只有 commentCreate → 只允许评论回写 | **PASS** | 不进行状态/标签变更 |
| GitLab CI 未 ready → 不允许真实 Factory dispatch | **PASS** | 不执行真实 dispatch |

---

*审计报告结束*
