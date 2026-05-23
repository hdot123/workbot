# Linear 模板设计：GitLab CI / Pipeline 验收模板

> 文档编号：ARCH-CI-001  
> 版本：V1.0（推演设计，非实现）  
> 创建日期：2026-05-04  
> 维护人：bailian-03  
> 状态：推演中

---

## 1. 为什么 CI 验收独立于人工验收

### 1.1 独立理由

| 维度 | 人工验收 | CI 验收 |
|------|---------|---------|
| 执行主体 | 人（agent / reviewer） | 机器（GitLab CI Runner） |
| 可重复性 | 依赖个人判断，不可完全重复 | 确定性执行，完全可重复 |
| 证据来源 | 截图、描述、口头确认 | pipeline/job 日志、artifacts、status code |
| 门禁角色 | 辅助判断、质量观察 | **唯一机器验收门禁** |
| 失败处理 | 可以主观放行 | 自动阻断，无主观放行 |
| 追溯性 | 弱（依赖人写报告） | 强（GitLab 永久留存 pipeline 记录） |

### 1.2 核心原则

1. **CI 是唯一的机器验收门禁**：任何需要自动化验证的内容，必须走 CI，不得以人工确认为替代。
2. **CI 与人工验收互补但不重叠**：人工验收关注设计质量、业务合理性、文档完整性；CI 验收关注代码正确性、测试通过率、构建状态、安全扫描。
3. **CI failed/canceled/skipped 均不得通过**：三种状态均视为验收不通过，只有 `success` 状态才视为 CI 验收通过。

---

## 2. 适用场景与不适用场景

### 2.1 适用场景

| 场景 | 说明 | CI 验证方式 |
|------|------|-------------|
| 代码提交合并 | 任何代码变更必须通过 CI 门禁 | pipeline → test/lint/build |
| 配置变更 | n8n workflow、nginx 配置变更 | pipeline → validate/deploy-test |
| 文档规范检查 | Markdown 格式、编号一致性 | pipeline → doc-lint |
| 安全扫描 | 依赖漏洞、secrets 泄露 | pipeline → security-scan |
| 数据库迁移 | schema 变更验证 | pipeline → migration-test |
| 镜像构建 | Docker image 构建和推送 | pipeline → build-and-push |

### 2.2 不适用场景

| 场景 | 说明 | 原因 | 替代方式 |
|------|------|------|---------|
| 业务合理性评审 | 产品设计、策略选择是否符合教育场景 | 无法自动化判断 | 人工评审（6+1 评审机制） |
| 用户体验评估 | 界面是否友好、交互是否合理 | 无法用代码验证 | 试点用户反馈 |
| 文档内容质量 | 文档是否清晰、完整、可理解 | LLM 辅助但不作为门禁 | 人工评审 |
| 架构合理性 | 模块拆分是否合理、依赖是否清晰 | 无法自动化判断 | 架构评审 |
| 试点运营效果 | 学校使用反馈、学生成长数据 | 需要实际运营数据 | 试点运营报告 |

---

## 3. 字段设计

### 3.1 必填字段

| 字段名 | 类型 | 说明 | 校验规则 |
|--------|------|------|---------|
| `linear_issue_id` | string | Linear Issue ID（如 AE-123） | 必须匹配 Linear Issue 格式 |
| `linear_issue_url` | string | Linear Issue 完整 URL | 必须可访问 |
| `gitlab_project_path` | string | GitLab 项目路径（如 group/repo） | 必须存在 |
| `pipeline_id` | number | GitLab Pipeline ID | 必须为正整数 |
| `pipeline_url` | string | GitLab Pipeline 完整 URL | 必须可访问 |
| `pipeline_status` | enum | Pipeline 最终状态 | 仅限 `success`（其他均不通过） |
| `branch_name` | string | 合并的分支名 | 不得为 main/develop 直接推送 |
| `commit_sha` | string | 最终合并的 commit SHA | 必须为 40 位 hex |
| `ci_validation_timestamp` | string | CI 验收时间（ISO 8601） | 必须在 Linear Issue 关闭之前 |
| `required_jobs_passed` | array[string] | 必须通过的 Job 名称列表 | 不得为空 |

### 3.2 可选字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `pipeline_duration_seconds` | number | Pipeline 总耗时（秒） |
| `test_coverage_percent` | number | 测试覆盖率百分比 |
| `security_scan_passed` | boolean | 安全扫描是否通过 |
| `lint_passed` | boolean | 代码风格检查是否通过 |
| `build_artifacts` | array[string] | 构建产物列表（artifacts URL） |
| `test_summary_url` | string | 测试报告 URL |
| `rollback_pipeline_id` | number | 回滚 Pipeline ID（如有） |
| `github_push_gate_id` | string | GitHub Push Gate 记录 ID（如涉及 GitHub 同步） |
| `webhook_event_ids` | array[string] | 触发的 Webhook 事件 ID 列表 |
| `supabase_audit_id` | string | Supabase 审计记录 ID |
| `n8n_workflow_execution_ids` | array[string] | n8n 工作流执行 ID 列表 |
| `notes` | string | 补充说明 |

---

## 4. 验收标准

### 4.1 CI 验收通过条件（全部必须满足）

| # | 条件 | 验证方法 | 不满足后果 |
|---|------|---------|-----------|
| C1 | `pipeline_status` == `success` | 检查 GitLab API / webhook | ❌ 验收不通过 |
| C2 | 所有 `required_jobs_passed` 中的 Job 状态为 `success` | 检查每个 Job 的 status | ❌ 验收不通过 |
| C3 | 无任何 Job 状态为 `failed` | 遍历所有 jobs | ❌ 验收不通过 |
| C4 | 无任何 Job 状态为 `canceled` | 遍历所有 jobs | ❌ 验收不通过 |
| C5 | 无任何 Job 状态为 `skipped` | 遍历所有 jobs | ❌ 验收不通过 |
| C6 | `commit_sha` 存在于该 pipeline 中 | GitLab API 验证 | ❌ 验收不通过 |
| C7 | `ci_validation_timestamp` 在 Issue 关闭之前 | 时间对比 | ❌ 验收不通过 |
| C8 | `branch_name` 不是受保护分支直接推送 | 分支保护规则检查 | ❌ 验收不通过 |

### 4.2 CI 验收不通过的枚举

| 状态 | 含义 | 是否允许人工放行 |
|------|------|-----------------|
| `failed` | 至少一个 Job 失败 | ❌ 绝对不允许 |
| `canceled` | Pipeline 被手动取消 | ❌ 绝对不允许 |
| `skipped` | Pipeline 被跳过 | ❌ 绝对不允许 |
| `pending` | Pipeline 尚未完成 | ⏳ 等待完成 |
| `running` | Pipeline 正在执行 | ⏳ 等待完成 |
| `manual` | 需要手动触发的 Job 未执行 | ❌ 必须执行 |
| `scheduled` | 定时任务尚未触发 | ⏳ 等待触发 |

### 4.3 硬性规则

```
IF pipeline_status != "success" → 验收不通过
IF any job.status in ["failed", "canceled", "skipped"] → 验收不通过
IF 涉及 GitHub 同步 AND 未走 GitHub Push Gate → 验收不通过
```

---

## 5. 证据要求

### 5.1 必须提供的证据

| 证据类型 | 来源 | 格式 | 用途 |
|---------|------|------|------|
| Pipeline 状态截图 | GitLab Web UI 或 API | URL / JSON | 证明 pipeline 最终状态 |
| Job 列表及状态 | GitLab API `/jobs` 端点 | JSON array | 证明所有 required jobs 通过 |
| Pipeline 日志 URL | GitLab Web UI | URL | 支持人工复查 |
| Commit 链接 | GitLab Web UI | URL | 证明代码版本对应 |
| 测试报告（如有） | Pipeline artifacts | URL / HTML | 证明测试细节 |
| 安全扫描报告（如有） | Pipeline artifacts | URL / JSON | 证明安全合规 |

### 5.2 证据存储位置

```
workspace/memory/tmp/ci-evidence/
├── <linear-issue-id>/
│   ├── pipeline-status.json          # Pipeline 状态快照
│   ├── jobs-list.json                # 所有 Job 状态列表
│   ├── required-jobs-passed.json     # 必填 Job 通过证明
│   ├── commit-info.json              # Commit 信息
│   └── validation-record.md          # 验收记录（本模板填充后）
```

### 5.3 证据不可变性

- Pipeline ID、Job ID、Commit SHA 一经记录不得修改
- 如发现证据有误，必须新建验证记录，不得覆盖原记录
- 历史验证记录永久保留在 `workspace/memory/tmp/ci-evidence/` 中

---

## 6. CI 需求判断

### 6.1 是否需要 CI

| 变更类型 | 是否需要 CI | 说明 |
|---------|------------|------|
| 代码变更（.py, .ts, .js 等） | ✅ 必须 | 运行 test/lint/build |
| 配置文件变更（.yml, .env, .json 等） | ✅ 必须 | 运行 validate |
| 文档变更（.md） | ⚠️ 可选 | 运行 doc-lint（如启用） |
| 纯 Linear Issue 状态变更（无代码） | ❌ 不需要 | 不涉及 CI |
| GitLab MR 合并 | ✅ 必须 | merge 前 pipeline 必须通过 |

### 6.2 CI Pipeline 必须包含的最低 Jobs

| Job 名称 | 用途 | 失败后果 |
|---------|------|---------|
| `lint` | 代码风格检查 | 阻断合并 |
| `test` | 单元测试 + 集成测试 | 阻断合并 |
| `build` | 构建验证（如适用） | 阻断合并 |
| `security-scan` | 安全扫描（如适用） | 阻断合并 |

---

## 7. GitHub Push Gate 规则

### 7.1 是否允许 GitHub push

**默认规则：不允许直接从 GitLab 同步到 GitHub。**

| 场景 | 是否允许 | 前置条件 |
|------|---------|---------|
| GitLab 代码仓库 → GitHub 镜像 | ⚠️ 有条件允许 | 必须走 GitHub Push Gate |
| 任何绕过 Gate 的直接 push | ❌ 绝对不允许 | — |
| 人工在 GitHub 上直接修改 | ❌ 绝对不允许 | — |

### 7.2 GitHub Push Gate 定义

```
GitHub Push Gate 是一个中间验证层，确保：
1. 代码已经通过 GitLab CI 验收（pipeline_status == success）
2. 合并到的目标分支是受保护的
3. 同步操作有完整的审计记录
```

### 7.3 Push 前置条件

| # | 条件 | 验证方式 |
|---|------|---------|
| G1 | GitLab CI pipeline 状态为 `success` | 检查 pipeline_status |
| G2 | 所有 required jobs 状态为 `success` | 检查 jobs list |
| G3 | MR 已经合并到目标分支 | 检查 MR 状态 |
| G4 | CI 验收记录已填写（本模板） | 检查验证记录存在 |
| G5 | 无未解决的安全扫描告警 | 检查 security-scan 结果 |
| G6 | 回滚方案已就绪（如涉及生产部署） | 检查 rollback 记录 |

### 7.4 GitHub Push Gate 拒绝枚举

| 条件不满足 | 拒绝原因 |
|-----------|---------|
| G1 不满足 | CI 未通过，禁止同步 |
| G2 不满足 | 关键 Job 未通过，禁止同步 |
| G3 不满足 | MR 未合并，禁止同步 |
| G4 不满足 | 无验收记录，禁止同步 |
| G5 不满足 | 有安全告警，禁止同步 |
| G6 不满足 | 无回滚方案，禁止同步 |

---

## 8. Webhook / Supabase / n8n 证据需求

### 8.1 Webhook 证据

| 事件 | 证据字段 | 来源 | 说明 |
|------|---------|------|------|
| Pipeline 状态变更 webhook | `webhook_event_ids` | n8n / nginx 日志 | 证明 webhook 已被接收和处理 |
| MR 合并 webhook | `webhook_event_ids` | n8n / nginx 日志 | 证明 MR 合并事件已被接收 |
| Push 事件 webhook | `webhook_event_ids` | n8n / nginx 日志 | 证明 push 事件已被接收 |

**验收要求**：
- Webhook 必须在 CI 通过后被正确触发
- Webhook 事件必须在 n8n 中成功处理
- Webhook 失败不得影响 CI 验收通过（但需要记录告警）

### 8.2 Supabase 证据

| 记录类型 | 字段 | 来源 | 说明 |
|---------|------|------|------|
| CI 验收记录 | `supabase_audit_id` | Supabase audit 表 | 证明验收结果已持久化 |
| Pipeline 状态记录 | `supabase_audit_id` | Supabase pipeline_status 表 | 证明 pipeline 状态已记录 |
| GitHub Push Gate 记录 | `supabase_audit_id` | Supabase push_gate 表 | 证明 Gate 检查已执行 |

**验收要求**：
- 所有 CI 验收结果必须写入 Supabase
- Supabase 记录必须与 GitLab 实际状态一致
- Supabase 审计记录不可删除或修改

### 8.3 n8n 证据

| 工作流 | 字段 | 来源 | 说明 |
|--------|------|------|------|
| GitLab Pipeline Handler | `n8n_workflow_execution_ids` | n8n 执行日志 | 证明 pipeline 事件已处理 |
| GitLab MR Handler | `n8n_workflow_execution_ids` | n8n 执行日志 | 证明 MR 事件已处理 |
| GitHub Push Gate | `n8n_workflow_execution_ids` | n8n 执行日志 | 证明 Gate 检查已执行 |
| Linear Issue Sync | `n8n_workflow_execution_ids` | n8n 执行日志 | 证明 Linear 状态已同步 |

**验收要求**：
- n8n 工作流执行必须成功（无 error 状态）
- n8n 执行日志必须包含完整的输入输出
- n8n 失败不得影响 CI 验收通过（但需要记录告警并人工跟进）

---

## 9. 回滚需求

### 9.1 何时需要回滚

| 触发条件 | 回滚类型 | 紧急程度 |
|---------|---------|---------|
| CI 通过后发现严重 Bug | 代码回滚 | 🔴 紧急 |
| 安全扫描遗漏的漏洞被发现 | 代码回滚 + 安全修复 | 🔴 紧急 |
| 部署后系统异常 | 部署回滚 | 🔴 紧急 |
| 数据迁移失败 | 数据回滚 | 🔴 紧急 |
| 配置错误导致服务不可用 | 配置回滚 | 🟡 高 |

### 9.2 回滚前置条件

| # | 条件 | 说明 |
|---|------|------|
| R1 | 回滚目标版本的 CI 记录存在 | 必须确认回滚到哪个版本 |
| R2 | 回滚 Pipeline 必须通过 | 回滚代码本身也必须通过 CI |
| R3 | 回滚操作有审计记录 | 谁、何时、为什么回滚 |
| R4 | 回滚后必须重新执行 CI 验收 | 回滚后的状态必须验证 |
| R5 | 回滚如涉及 GitHub 同步，必须重新走 Push Gate | 防止不一致 |

### 9.3 回滚验收记录

回滚完成后，必须在原 CI 验收记录中追加：

```markdown
## 回滚记录

- 回滚原因：<原因描述>
- 回滚目标版本：<commit_sha>
- 回滚 Pipeline ID：<rollback_pipeline_id>
- 回滚 Pipeline 状态：success
- 回滚执行时间：<ISO 8601>
- 回滚执行人：<执行者>
- 回滚后 CI 验收：✅ 通过 / ❌ 未通过
- Supabase 回滚审计 ID：<supabase_audit_id>
```

---

## 10. Factory 子代理需求

### 10.1 参与子代理

| 子代理 | 职责 | 输出 |
|--------|------|------|
| `qa-bot` | CI 验收结果验证 | 验收通过/不通过结论 |
| `dev-bot` | 代码变更关联的 pipeline 状态确认 | pipeline 状态证据 |
| `pm-bot` | Linear Issue 状态与 CI 验收对齐 | Issue 状态更新 |
| `doc-bot` | CI 验收记录文档化 | 验收记录 Markdown |
| `rea-bot` | 回滚方案验证（如涉及） | 回滚可行性报告 |

### 10.2 协作流程

```
MR 合并 → GitLab CI Pipeline 执行
    │
    ├── pipeline success → qa-bot 确认验收通过
    │      │
    │      ├── doc-bot 生成验收记录（本模板）
    │      │      │
    │      │      ├── 写入 Supabase 审计
    │      │      └── 触发 n8n webhook 处理
    │      │
    │      └── 如涉及 GitHub 同步 → Push Gate 验证
    │             │
    │             ├── G1-G6 全部满足 → 允许 push
    │             └── 任一不满足 → 拒绝 push
    │
    └── pipeline failed/canceled/skipped → qa-bot 标记验收不通过
           │
           ├── 阻断 MR 合并
           └── 通知 dev-bot 修复
```

### 10.3 子代理权限限制

| 子代理 | 允许操作 | 禁止操作 |
|--------|---------|---------|
| `qa-bot` | 读取 pipeline 状态、写入验收结论 | 不得修改 CI 配置、不得手动通过 Job |
| `dev-bot` | 读取 pipeline 日志、修复代码 | 不得跳过 CI、不得修改 pipeline 结果 |
| `pm-bot` | 更新 Linear Issue 状态 | 不得在无 CI 验收通过的情况下关闭 Issue |
| `doc-bot` | 创建/更新验收记录文档 | 不得修改已有验收记录 |
| `rea-bot` | 验证回滚方案 | 不得执行回滚操作（需人工审批） |

---

## 11. 风险矩阵

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| CI pipeline 误报失败（flaky test） | 中 | 高 | 允许重试机制，但需记录 |
| CI pipeline 漏报通过（关键测试未覆盖） | 低 | 极高 | 定期审查测试覆盖率 |
| GitHub Push Gate 被绕过 | 低 | 极高 | Gate 必须由 n8n 自动执行，禁止人工 |
| Webhook 丢失导致状态不一致 | 中 | 高 | Supabase 定时对账 |
| n8n 工作流执行失败 | 中 | 中 | 告警 + 人工跟进 |
| Supabase 记录与实际不符 | 低 | 高 | 定时验证 GitLab 实际状态 |
| 回滚失败 | 低 | 极高 | 回滚前验证回滚版本 CI 状态 |

---

## 12. MVP 范围

### 12.1 MVP 必须包含

| # | 项目 | 说明 |
|---|------|------|
| M1 | Pipeline 状态检查 | 验证 pipeline_status == success |
| M2 | Required Jobs 检查 | 验证指定 jobs 全部通过 |
| M3 | CI 验收记录模板 | 本文档的 Linear Markdown 模板 |
| M4 | 证据存储结构 | `workspace/memory/tmp/ci-evidence/` 目录 |
| M5 | failed/canceled/skipped 阻断 | 三种状态均视为不通过 |

### 12.2 MVP 之后的增强

| 阶段 | 项目 | 说明 |
|------|------|------|
| V2 | GitHub Push Gate 自动化 | n8n 自动执行 Gate 检查 |
| V2 | Webhook 集成验证 | n8n pipeline event 处理 |
| V2 | Supabase 审计记录 | 验收结果持久化 |
| V3 | 回滚自动化 | 一键回滚到指定版本 |
| V3 | 测试覆盖率门禁 | 覆盖率低于阈值阻断合并 |
| V3 | 安全扫描门禁 | 高危漏洞阻断合并 |

---

## 13. Linear Markdown 模板

以下是可直接粘贴到 Linear Issue 描述或评论中的验收模板：

---

```markdown
## 🤖 CI / Pipeline 验收记录

> **CI 是唯一的机器验收门禁。CI failed / canceled / skipped 均不得通过。**

### 基本信息

| 字段 | 值 |
|------|-----|
| Linear Issue | [AE-XXX](linear-issue-url) |
| GitLab 项目 | `group/repo` |
| 分支 | `feature/xxx` |
| Commit SHA | `abc123def456...` |
| Pipeline ID | `1234` |
| Pipeline URL | [查看](pipeline-url) |
| Pipeline 状态 | ✅ success / ❌ failed |
| 验收时间 | `2026-05-04T12:00:00Z` |

### 必填 Jobs 验证

| Job 名称 | 状态 | 日志 URL |
|---------|------|---------|
| `lint` | ✅ success / ❌ failed | [查看](job-url) |
| `test` | ✅ success / ❌ failed | [查看](job-url) |
| `build` | ✅ success / ❌ failed | [查看](job-url) |
| `security-scan` | ✅ success / ❌ failed | [查看](job-url) |

### CI 验收结论

- [ ] C1: pipeline_status == success
- [ ] C2: 所有 required jobs 状态为 success
- [ ] C3: 无 Job 状态为 failed
- [ ] C4: 无 Job 状态为 canceled
- [ ] C5: 无 Job 状态为 skipped
- [ ] C6: commit_sha 存在于该 pipeline 中
- [ ] C7: ci_validation_timestamp 在 Issue 关闭之前
- [ ] C8: branch_name 不是受保护分支直接推送

**结论**: ✅ CI 验收通过 / ❌ CI 验收不通过（原因：______）

---

### GitHub Push Gate（如涉及 GitHub 同步）

- [ ] G1: GitLab CI pipeline 状态为 success
- [ ] G2: 所有 required jobs 状态为 success
- [ ] G3: MR 已经合并到目标分支
- [ ] G4: CI 验收记录已填写
- [ ] G5: 无未解决的安全扫描告警
- [ ] G6: 回滚方案已就绪

**Push Gate 结论**: ✅ 允许 push / ❌ 拒绝 push（原因：______）

---

### 证据清单

| 证据类型 | 位置 |
|---------|------|
| Pipeline 状态快照 | `workspace/memory/tmp/ci-evidence/<issue-id>/pipeline-status.json` |
| Job 列表 | `workspace/memory/tmp/ci-evidence/<issue-id>/jobs-list.json` |
| Required Jobs 通过证明 | `workspace/memory/tmp/ci-evidence/<issue-id>/required-jobs-passed.json` |
| Commit 信息 | `workspace/memory/tmp/ci-evidence/<issue-id>/commit-info.json` |
| 测试报告（如有） | [URL](test-report-url) |
| 安全扫描报告（如有） | [URL](security-report-url) |

---

### Webhook / Supabase / n8n 记录

| 系统 | 记录 ID | 状态 |
|------|---------|------|
| Webhook Event | `webhook-event-id-xxx` | ✅ 已处理 |
| Supabase Audit | `supabase-audit-id-xxx` | ✅ 已记录 |
| n8n Pipeline Handler | `n8n-exec-id-xxx` | ✅ 执行成功 |
| n8n MR Handler | `n8n-exec-id-xxx` | ✅ 执行成功 |

---

### 回滚记录（如已执行回滚）

- **回滚原因**: ______
- **回滚目标版本**: `commit_sha`
- **回滚 Pipeline ID**: `rollback_pipeline_id`
- **回滚 Pipeline 状态**: ✅ success
- **回滚执行时间**: `2026-05-04T14:00:00Z`
- **回滚执行人**: `agent-name`
- **回滚后 CI 验收**: ✅ 通过 / ❌ 未通过
- **Supabase 回滚审计 ID**: `supabase-rollback-id-xxx`
```

---

## 14. 与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| ARCH-CI-001 CI/Pipeline 验收模板 | SEC-ARCH-002 GitLab Webhook 架构 | webhook 事件触发 CI 状态同步 |
| ARCH-CI-001 CI/Pipeline 验收模板 | SEC-ARCH-001 Linear Webhook 安全架构 | Linear Issue 状态与 CI 验收对齐 |
| ARCH-CI-001 CI/Pipeline 验收模板 | ARCH-011 测试验收与灰度发布标准 | CI 验收是测试验收的机器门禁层 |
| ARCH-CI-001 CI/Pipeline 验收模板 | AGENTS.md Phase Git Convention | branch-1/branch-2 隔离下的 CI 验证 |

---

## 15. 注意事项

1. **本文件是推演设计，不是实现代码**：不修改任何 `.gitlab-ci.yml`、pipeline 配置或 n8n 工作流。
2. **CI failed/canceled/skipped 绝对不允许通过**：这是硬规则，不存在任何例外情况。
3. **GitHub Push Gate 是强制门禁**：涉及 GitHub 同步必须走 Gate，不得绕过。
4. **证据不可篡改**：所有 pipeline/job 证据一经记录不得修改，错误只能追加新记录。
5. **回滚本身也要通过 CI**：回滚操作不是特殊通道，回滚代码同样需要完整的 CI 验证。
6. **人工不得干预 CI 结果**：任何子代理或人都不能手动修改 pipeline 或 job 的状态。

---

**文档状态**：推演设计  
**审批人**：待定  
**下次评审日期**：待定
