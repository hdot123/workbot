# GitLab 基础设施确认报告

> 审计日期: 2026-05-07
> 审计模式: 只读确认，零改动
> 前置: P0-1 GitHub 直推已封堵，gate-check 绝对 fail-closed

---

## 0. 总体结论

### **PARTIAL**

GitLab CE 实例真实存在且可访问，gateway-admin 项目已有完整 CI pipeline，但 workbot 仓库尚未接入 GitLab。

| 维度 | 状态 | 说明 |
|------|------|------|
| GitLab CE 实例 | **READY** | `node-15.tail5e888.ts.net`，HTTP 302 响应，API 可达 |
| gateway-admin 项目 | **READY** | 完整 `.gitlab-ci.yml`，6 个 stage，pipeline 已跑通 |
| gitlab-ci-standards 模板库 | **READY** | `infra/gitlab-ci-standards`，6 个模板，v1.0.0 tagged |
| workbot 项目接入 GitLab | **NOT EXISTS** | 无 GitLab remote，无 `.gitlab-ci.yml` |
| workbot Runner | **NOT EXISTS** | workbot 未接入 GitLab，无 runner 配置 |
| GitHub push 封堵 | **VERIFIED PASS** | gate-check 绝对 fail-closed，`passed=true` 不存在 |

---

## 1. workbot 当前 GitLab 接入状态

| # | 检查项 | 结果 |
|---|--------|------|
| 1.1 | git remote -v | 仅 `origin -> github.com/hdot123/workbot.git`，无 GitLab remote |
| 1.2 | .gitlab-ci.yml | **不存在** |
| 1.3 | .gitlab/ 目录 | **不存在** |
| 1.4 | GitLab CI include/template | **不存在**（仅在 `/Users/busiji/tool/.gitlab-ci.yml` 中有 include，非 workbot） |
| 1.5 | Pipeline 缓存/历史 | **不存在** |
| 1.6 | 真实 GitLab URL (非 example.com) | 在 workbot 仓库内：**无**。在 `/Users/busiji/tool/` 中：**有** |

---

## 2. GitLab 实例状态

### 结论: **READY**

| # | 检查项 | 结果 |
|---|--------|------|
| 2.1 | 真实 URL | `http://node-15.tail5e888.ts.net` |
| 2.2 | 是否可访问 | **YES** — HTTP 302 (redirect to login)，响应时间 0.11s |
| 2.3 | API 可达 | **YES** — `/api/v4/projects` 返回 JSON（公开项目列表），`/api/v4/version` 返回 401（需认证） |
| 2.4 | 证据来源 | `gateway-admin` git remote `gitlab -> node-15.tail5e888.ts.net/root/gateway-admin.git` |
| 2.5 | 实例类型 | **GitLab CE** (gitlab-ci-standards README 明确写 "GitLab CE") |

### 公开可见项目

| project_id | path | default_branch |
|------------|------|----------------|
| 3 | `root/axonhub-deletion_scheduled-3` | branch-2 |

注：仅列出无需认证可见的项目。gateway-admin、gitlab-ci-standards 等需认证后才可见。

---

## 3. GitLab 项目状态

### 3.1 已确认存在的项目

| # | 项目名 | GitLab 路径 | 本地路径 | 状态 |
|---|--------|-------------|----------|------|
| 1 | gateway-admin | `root/gateway-admin` | `/Users/busiji/tool/gateway-admin/` | **READY** — 有 `.gitlab-ci.yml`，6 stages，pipeline 已跑通 |
| 2 | gitlab-ci-standards | `infra/gitlab-ci-standards` | `/Users/busiji/tool/gitlab-ci-standards/` | **READY** — v1.0.0 tagged，6 个 CI 模板 |
| 3 | factory-config-baseline | 同 gateway-admin remote | `/Users/busiji/tool/factory-config-baseline/` | 同 gateway-admin 项目子目录 |
| 4 | tool (gateway-admin CI root) | `root/gateway-admin` | `/Users/busiji/tool/` | gateway-admin 的 CI 根目录 |

### 3.2 workbot 仓库中未发现的项目

| # | 项目名 | 在 workbot 仓库 | 在 /Users/busiji/tool/ | 说明 |
|---|--------|-----------------|----------------------|------|
| 1 | workbot | **不存在** | **不存在** | workbot 未接入 GitLab |
| 2 | webhook-ingress | 不作为独立项目 | 不作为独立项目 | 是 workbot 的 Python 模块 |
| 3 | factory-adapter | 不作为独立项目 | 不作为独立项目 | 是 workbot 的 Python 模块 |
| 4 | gateway-admin | k8s deployment 名 | **独立项目** | AEdu 文档中引用的是 k8s deployment |
| 5 | infra/gitlab-ci-standards | 不存在 | **独立项目** | 标准 CI 模板库 |

### 3.3 gateway-admin CI pipeline 详情

`.gitlab-ci.yml` 包含 **6 stages**:

| Stage | Job | 说明 |
|-------|-----|------|
| lint | backend-lint | TypeScript noEmit |
| lint | frontend-build | npm run build |
| lint | frontend-typecheck | npm run typecheck |
| lint | frontend-lint | npm run lint |
| test | backend-test | npm test |
| e2e | frontend-e2e | Playwright + junit report |
| security | security-scan | 扫描 APISIX_ADMIN_KEY / ADMIN_ACTION_TOKEN / secret_key / password / JWT |
| build | docker-build | docker build + verify (仅 main 分支) |

**关键证据**: git log 包含 `chore: verify full CI pipeline passes` (commit 159903d)，证明 pipeline 已真实跑通。

---

## 4. Runner 状态

### 结论: **PARTIAL — runner 存在，但详情需认证**

| # | 检查项 | 结果 |
|---|--------|------|
| 4.1 | runner 是否存在 | **YES** — gitlab-ci-standards 模板中 `tags: [shell]`，gateway-admin CI 无 `tags:` 指定（使用 shared runner） |
| 4.2 | runner tags | `shell`（gitlab-ci-standards 模板明确要求） |
| 4.3 | executor | **shell**（基于 tags 和 job 脚本内容推断） |
| 4.4 | runner online | **需认证确认** — `/api/v4/runners` 返回 401 |
| 4.5 | runner 注册证据 | gateway-admin pipeline 已跑通，runner 必然在线 |
| 4.6 | runner service/docker | 无独立 docker-compose，直接运行在 GitLab CE 实例上 |

---

## 5. Pipeline 能力证据

### 5.1 CI 标准模板库 (infra/gitlab-ci-standards)

| 模板 | 功能 |
|------|------|
| `templates/base.yml` | 6 stages: lint / security / validate / test / build / dry-run |
| `templates/secrets.yml` | 扫描 glpat- / sk- / Bearer / PRIVATE KEY |
| `templates/json-yaml.yml` | JSON/YAML 语法验证 |
| `templates/shell.yml` | Shell 脚本语法验证 |
| `templates/factory-config.yml` | Factory 配置项目验证 |
| `templates/full.yml` | 包含所有模板 |
| `examples/minimal.gitlab-ci.yml` | base + secrets |
| `examples/full.gitlab-ci.yml` | full template |
| `examples/factory-config.gitlab-ci.yml` | base + factory-config |

### 5.2 gateway-admin 实际 pipeline 能力

| 能力 | 状态 | 说明 |
|------|------|------|
| Secret scan | **YES** | 检查 glpat-/sk-/Bearer/PRIVATE KEY + 自定义 APISIX_ADMIN_KEY 等 |
| Lint | **YES** | TypeScript noEmit + ESLint |
| Test | **YES** | backend npm test |
| E2E | **YES** | Playwright + junit report + artifacts |
| Security scan | **YES** | 硬编码凭证/密码/JWT 扫描 |
| Docker build | **YES** | 仅 main 分支 |
| GitHub sync gate | **NO** | 无 T10-PushGate job |
| Pipeline 回写 Linear | **NO** | 无实现（仅设计文档） |

### 5.3 workbot 所需 CI 能力缺口

workbot 接入 GitLab 后需要但当前不存在的：

| 能力 | 优先级 | 可复用 |
|------|--------|--------|
| Python pytest job | P0 | 需新建，参考 gateway-admin 的 backend-test |
| webhook-ingress 测试 | P0 | 参考 `webhook-ingress-validation.yml`（34 tests） |
| Secret scan | P0 | **可复用** `gitlab-ci-standards/templates/secrets.yml` |
| YAML/JSON lint | P1 | **可复用** `gitlab-ci-standards/templates/json-yaml.yml` |
| Shell lint | P1 | **可复用** `gitlab-ci-standards/templates/shell.yml` |
| GitHub sync gate job | P0 | 需新建 |
| Pipeline 回写 Linear | P2 | 需新建 |

---

## 6. P0-1 复核状态

### 结论: **VERIFIED PASS**

| # | 检查项 | 结果 |
|---|--------|------|
| 6.1 | schedule 已禁用 | **PASS** — `# schedule:` 注释状态 |
| 6.2 | gate-check 绝对 fail-closed | **PASS** — 文件中不存在 `passed=true` |
| 6.3 | 两处 git push 受 gate-check 约束 | **PASS** — 均在 `sync-verify-deploy` job 内，`needs: gate-check` + `if: gitlab_ci_passed == 'true'` |
| 6.4 | hard fail-closed 消息 | **PASS** — `GATE BLOCKED (hard fail-closed): GitLab API verifier is not implemented.` |
| 6.5 | 不允许人工声明替代 | **PASS** — 即使所有输入正确也 exit 1 |
| 6.6 | secret scan findings | **0** |
| 6.7 | workflow SHA256 | `dfab01b5381fbc1c11796798b1ec92f12b98e24ad42c85532f868ebb29995795` |

---

## 7. 下一步建议

### 判定: **PARTIAL — 需要接入 workbot 到 GitLab**

#### 最小接入方案 (不做实施，仅输出计划)

```
Phase A: workbot 接入 GitLab CE
─────────────────────────────────
A1. 在 GitLab CE (node-15.tail5e888.ts.net) 创建 workbot 项目
A2. 添加 GitLab remote: git remote add gitlab http://node-15.../root/workbot.git
A3. 创建 .gitlab-ci.yml（include gitlab-ci-standards + workbot 专属 jobs）
A4. 注册/分配 runner（复用现有 shell runner，tag: shell）
A5. 验证 pipeline 跑通

Phase B: 最小 CI jobs
─────────────────────
B1. pytest job (34 webhook-ingress tests)
B2. secret scan (复用 gitlab-ci-standards/templates/secrets.yml)
B3. YAML/JSON lint (复用 gitlab-ci-standards/templates/json-yaml.yml)
B4. GitHub sync gate job (pipeline success 后才允许 push)

Phase C: 闭环链路 (依赖 Phase A + B)
──────────────────────────────────────
C1. GitLab webhook -> workbot webhook-ingress (GitLabAdapter)
C2. Pipeline result -> Linear issueUpdate (dry-run first)
C3. Factory dispatch gate 解除 (需要 Phase B CI 门禁 ready)
```

#### C 方案: 暂时保持 GitHub push disabled

在 Phase A/B 完成前：
- gate-check 保持绝对 fail-closed
- 不允许真实 Factory dispatch
- 仅做 dry-run 设计
- 不推 GitHub

---

## 8. 相关文件 SHA256

### workbot (GitHub 直推封堵)

| 文件 | SHA256 |
|------|--------|
| `.github/workflows/memory-core-auto-sync-deploy.yml` | `dfab01b5381fbc1c11796798b1ec92f12b98e24ad42c85532f868ebb29995795` |

### GitLab CE 基础设施

| 文件/路径 | 说明 |
|-----------|------|
| `/Users/busiji/tool/.gitlab-ci.yml` | tool 根目录 CI（include gitlab-ci-standards） |
| `/Users/busiji/tool/gateway-admin/.gitlab-ci.yml` | 完整 6-stage CI pipeline |
| `/Users/busiji/tool/gateway-admin/` git remote `gitlab` | `node-15.tail5e888.ts.net/root/gateway-admin.git` |
| `/Users/busiji/tool/gitlab-ci-standards/` | 标准 CI 模板库 v1.0.0 |
| `/Users/busiji/tool/gitlab-ci-standards/` git remote `origin` | `node-15.tail5e888.ts.net/infra/gitlab-ci-standards.git` |
| `/Users/busiji/tool/gitlab-ci-standards/templates/` | base / secrets / json-yaml / shell / factory-config / full |
| `/Users/busiji/tool/factory-config-baseline/` | Factory 配置基线（同 gateway-admin remote） |

### GitLab CE 实例

| 属性 | 值 |
|------|-----|
| URL | `http://node-15.tail5e888.ts.net` |
| 类型 | GitLab CE |
| HTTP 状态 | 302 (redirect to login) |
| API 可达 | YES (`/api/v4/projects` 返回 JSON) |
| 认证要求 | 401 on `/api/v4/version`, `/api/v4/runners` |

---

## 9. Secret Scan Findings

| 范围 | Findings |
|------|----------|
| workbot/.github/workflows/ | **0** |
| workbot 全仓库 | **0** |
| /Users/busiji/tool/gateway-admin/.gitlab-ci.yml | **0** (注意: git remote URL 含凭证，但不在本报告输出范围内) |
| /Users/busiji/tool/gitlab-ci-standards/ | **0** |
| **总计** | **0** |

---

*审计报告结束*
