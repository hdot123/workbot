# Linear 普通开发任务模板设计

> 文档编号：PM-TPL-001  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-02  
> 状态：设计草案  
> 约束：只设计不执行；不得调用外部 API；不得改任何配置；不得创建真实模板；不得推送 GitHub

---

## 一、为什么需要独立模板

### 1.1 定位

普通开发任务模板是 Linear Issue 级别的**任务描述标准**，用于指导 cmux 体系下的 `dev-bot` 完成单个可交付的编码任务。

它独立存在的原因：

| 对比项 | 已有模板/体系 | 本模板 |
|--------|-------------|--------|
| `AEdu/dev-task-list.md` | 项目内部手工登记表，不依赖 Linear | Linear 原生模板，与 webhook → n8n → Linear 链路对齐 |
| `OPS-LINEAR-006 acceptance template` | 验收报告模板，面向 dry-run 验收 | 面向日常编码任务，是开发视角 |
| `task-dispatch-playbook.md` | 指挥官派单手册，非模板 | 本模板是派单落地后 Linear 上的实际内容格式 |
| Phase Git Convention (`branch-2`) | Git 操作约定 | 本模板将其包装为 Linear 字段和验收标准 |

### 1.2 独立价值

- **标准化输入**：确保每个普通开发任务在 Linear 上具备相同的信息密度
- **CI Gate 前置**：所有涉及代码的任务必须要求 GitLab CI 通过前不得 Done
- **证据分层**：普通任务不要求 raw/canonical/n8n/Supabase 证据，仅在发布/同步任务中要求
- **防误推 GitHub**：100% 禁止直接推送 GitHub，模板内置约束

---

## 二、适用范围

### 2.1 适用场景

| 场景 | 示例 |
|------|------|
| Bug 修复 | 修复测试失败、逻辑错误 |
| 新功能开发 | 新增模型、接口、脚本 |
| 重构 | 模块拆分、函数重组 |
| 测试补充 | 新增/修复单元测试、集成测试 |
| 小型文档更新 | README 更新、注释补全（与代码一起提交） |

### 2.2 不适用场景

| 场景 | 原因 | 应该使用 |
|------|------|---------|
| 发布/版本同步 | 需要 GitHub Push Gate + raw/canonical 证据 | 发布任务专用模板 |
| 架构级重构 | 涉及多个 Phase、多 bot 协作 | Phase 任务模板（M*/P*/H*） |
| Security Audit | 需要 STRIDE/OWASP 审查 | security-review skill |
| CI/CD 基础设施变更 | 涉及 n8n/nginx/webhook 配置 | OPS 任务模板 |
| 纯文档/知识管理 | 不涉及代码 | doc-bot 内部约定 |

---

## 三、字段定义

### 3.1 必填字段

| 字段名 | Linear 对应 | 类型 | 说明 |
|--------|-----------|------|------|
| `title` | Issue 标题 | 文本 | 格式：`type(scope): 简短描述`（Conventional Commits 风格） |
| `description` | Issue 描述（Markdown body） | Markdown | 模板主体，见 §3.3 |
| `team` | Linear Team | 选择器 | 指定所属团队（如 JTO） |
| `priority` | Linear Priority | 选择器 | Urgent / High / Medium / Low |
| `labels` | Linear Labels | 多选 | `dev-task` + 至少 1 个分类标签（`bug` / `feature` / `refactor` / `test` / `chore`） |
| `status` | Linear Status | 状态 | 任务流转：Backlog → Ready → In Progress → In Review → Done |
| `parent` | Parent Issue | 可选关联 | 关联到更大的 Epic / Phase |
| `estimation` | Linear Estimation | 数字 | Story Points（1/2/3/5/8） |

### 3.2 可选字段

| 字段名 | Linear 对应 | 类型 | 说明 |
|--------|-----------|------|------|
| `subtasks` | Sub-issues | 子任务列表 | 任务需要拆分为多个子步骤时使用 |
| `blockedBy` | Blocking issues | 关联 | 有外部依赖时标记 |
| `blocking` | Blocked issues | 关联 | 阻塞了其他任务时标记 |
| `custom:branch` | Custom Field | 文本 | 临时 branch-2 分支名（如 `branch-2/fix-ocr-20260504`） |
| `custom:write_scope` | Custom Field | 文本 | 允许修改的文件/目录范围 |

### 3.3 Description 模板结构

Issue 描述的 Markdown body 必须包含以下段落（顺序固定）：

```markdown
# [type(scope)] 任务标题

## 上下文
[2-3 句话说明任务的背景、为什么做、与哪些已有文件/模块相关]

## 当前状态依据
- 本地 task-list: [引用 dev-task-list.md 中相关条目]
- CE: [CE Issue 编号，如有]
- 代码/测试现场: [关键文件或测试结果]

## 目标
1. [具体目标 1]
2. [具体目标 2]

## 修改范围 (write_scope)
- [允许修改的文件/目录/模块]

## 禁止事项
- [明确禁止的操作，如禁止改配置、禁止动数据库]

## Git 操作约定
- 从 `branch-1` 创建临时 `branch-2`
- 所有代码工作必须在 `branch-2` 上完成
- 完成后: scoped git add → commit on branch-2 → merge into branch-1 → push branch-1 → 写 SHA 到证据

## 最小验证
- [必须运行的测试/检查]
- [通过标准]

## 验收标准
- [ ] GitLab CI 通过（硬性前置，不得跳过）
- [ ] 本地 pytest/类型检查通过
- [ ] 无新增 warning
- [ ] 所有修改在 write_scope 范围内
- [ ] 未触碰禁止项

## 交付物
- [列出期望的文件变更、测试、文档]

## 备注
[其他说明]
```

---

## 四、验收标准

### 4.1 硬性验收（不满足不得 Done）

| # | 验收项 | 验证方式 | 说明 |
|---|--------|---------|------|
| H1 | GitLab CI 通过 | CI Pipeline status = success | **硬性前置**，所有涉及代码的任务必须 CI 通过前不得 Done |
| H2 | 本地测试通过 | `pytest` / 对应测试命令 | 本地最小验证通过 |
| H3 | 无新增 warning | 测试输出 `0 warnings` | 不引入新 warning |
| H4 | 分支约定已遵守 | Git log 验证 branch-2 创建 → 合并路径 | 不得直接在 branch-1 上修改 |
| H5 | 未直接推送 GitHub | Git remote 验证 push 目标为 GitLab | **100% 禁止直接推送 GitHub** |

### 4.2 软性验收（建议满足）

| # | 验收项 | 验证方式 | 说明 |
|---|--------|---------|------|
| S1 | commit message 规范 | Conventional Commits 格式检查 | `type(scope): description` |
| S2 | 代码审查 | rea-bot 或人工 review | 审计密集期必须 rea-bot 首轮 |
| S3 | 文档同步 | 相关文档已更新 | 代码变更影响文档时 |
| S4 | branch-2 已清理 | 分支已删除或标记退役 | 不保留无用临时分支 |

---

## 五、证据要求

### 5.1 普通开发任务的证据要求

**核心原则**：普通开发任务**不应要求** raw / canonical / n8n / Supabase 证据。

| 证据类型 | 是否要求 | 说明 |
|---------|---------|------|
| GitLab CI Pipeline 状态截图/链接 | ✅ 必填 | 证明 CI 通过 |
| 本地测试输出 | ✅ 必填 | pytest / 对应测试命令输出 |
| Git commit SHA | ✅ 必填 | branch-2 的 commit hash |
| 修改文件列表 | ✅ 必填 | git diff --name-only 输出 |
| branch-2 合并记录 | ✅ 必填 | merge commit 记录 |
| raw webhook 事件 | ❌ 不要求 | 仅在 webhook 相关任务中要求 |
| canonical event | ❌ 不要求 | 仅在 webhook 相关任务中要求 |
| n8n execution log | ❌ 不要求 | 仅在发布/同步任务中要求 |
| Supabase 查询结果 | ❌ 不要求 | 仅在 webhook/数据相关任务中要求 |

### 5.2 发布/同步任务的额外证据要求

当任务涉及**发布或同步**（如版本发布、跨系统同步）时，额外要求：

| 证据类型 | 说明 |
|---------|------|
| GitHub Push Gate 记录 | 证明推送 GitHub 经过了审批门控 |
| n8n execution log | 同步 workflow 执行记录 |
| Supabase 查询结果 | 数据一致性验证 |
| raw/canonical 事件对照 | 数据转换正确性验证 |

**但普通开发任务不包含上述要求。**

---

## 六、CI 要求

### 6.1 是否需要 CI

**是。所有涉及代码的普通开发任务必须要求 GitLab CI 通过前不得 Done。**

这是硬性验收标准 H1，不可跳过、不可豁免。

### 6.2 CI 内容

| CI Stage | 说明 |
|----------|------|
| `lint` | 代码风格检查 |
| `test` | 单元测试 + 集成测试 |
| `typecheck` | 类型检查（如适用） |
| `build` | 构建验证（如适用） |

---

## 七、GitHub Push 规则

### 7.1 是否允许 GitHub Push

**不允许。**

普通开发任务 100% 禁止直接推送 GitHub。

### 7.2 Push 前置条件（仅适用于发布/同步任务）

当任务确实需要推送 GitHub 时（如版本发布），必须满足：

| # | 前置条件 | 说明 |
|---|---------|------|
| G1 | GitLab CI 全部通过 | 所有 stage 均为 success |
| G2 | QA 验收通过 | qa_done 状态已确认 |
| G3 | 文档已同步 | doc_synced 状态已确认 |
| G4 | 人工审批 | 指挥官/负责人明确批准 |
| G5 | Push Gate 记录 | 在 Linear Issue 中记录审批人和时间 |

**普通开发任务不触发上述流程。**

---

## 八、Webhook / Supabase / n8n 证据需求

### 8.1 普通开发任务

| 系统 | 是否要求证据 | 说明 |
|------|------------|------|
| Webhook ingress | ❌ 不要求 | 除非任务本身涉及 webhook 代码 |
| Supabase | ❌ 不要求 | 除非任务本身涉及数据库变更 |
| n8n | ❌ 不要求 | 除非任务本身涉及 n8n workflow |

### 8.2 涉及 webhook/数据任务的额外要求

当任务本身涉及 webhook ingress、Supabase 数据变更或 n8n workflow 修改时：

| 系统 | 要求 | 说明 |
|------|------|------|
| Webhook ingress | ✅ 需要 raw/canonical 对照 | 验证事件格式正确 |
| Supabase | ✅ 需要 SQL 查询结果 | 验证数据写入正确 |
| n8n | ✅ 需要 execution log | 验证 workflow 执行成功 |

---

## 九、回滚需求

### 9.1 是否需要回滚预案

**是。每个普通开发任务必须在 description 中包含回滚策略。**

### 9.2 回滚策略模板

```markdown
## 回滚策略

### 回滚触发条件
- [ ] GitLab CI 失败且无法修复
- [ ] 引入回归错误（测试发现）
- [ ] 生产环境异常

### 回滚操作
1. 在 `branch-1` 上 revert 对应的 merge commit
2. 验证 revert 后测试全部通过
3. 更新 Linear Issue 状态为 `blocked` 或 `canceled`
4. 在 `next_step` 中记录回滚原因和后续计划

### 回滚约束
- 已推送至 GitLab 的 commit 必须通过 revert 撤销，不得 force push
- 已同步至下游系统的变更需通知相关方
```

---

## 十、Factory 子代理需求

### 10.1 是否需要子代理

**视任务复杂度而定。**

### 10.2 子代理分配规则

| 任务属性 | 需要的子代理 | 说明 |
|---------|-------------|------|
| 审计/复核/review | `rea-bot` 首轮 | 必须先审计再决定是否转 dev |
| 编码/修复 | `dev-bot` | 主要执行者 |
| 测试补充 | `qa-bot` | 可直接派 qa-bot |
| 文档更新 | `doc-bot` | 可直接派 doc-bot |
| 复杂重构 | `bailian-worker` | 通过 Skill 调用，处理多文件联动 |

### 10.3 bailian-worker 使用场景

| 场景 | 说明 |
|------|------|
| 大型代码重构 | 涉及 5+ 文件的结构性改动 |
| 多文件联动修改 | 修改一个模块需要同步修改多个依赖模块 |
| 复杂 bug 修复 | 需要深入分析调用链和数据流 |
| 自动化测试编写 | 需要编写大量测试用例 |

---

## 十一、风险

### 11.1 风险矩阵

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| CI 通过但功能未验证 | 中 | 高 | 本地测试必须包含功能验证用例 |
| branch-2 未合并导致丢失 | 低 | 高 | 严格执行 merge → push → 写 SHA 流程 |
| write_scope 越界 | 中 | 中 | 验收时检查 diff --name-only |
| GitHub 误推 | 低 | 极高 | GitLab CI 配置中禁止 GitHub remote，模板中明确禁止 |
| 回滚失败 | 低 | 高 | 回滚后必须重新运行全量测试 |

### 11.2 常见陷阱

| 陷阱 | 预防 |
|------|------|
| 在 branch-1 上直接修改 | 模板强制要求从 branch-1 创建 branch-2 |
| 跳过 CI 直接 Done | 验收标准 H1 硬性要求 |
| 证据写进代码路径 | 证据应留在 memory/tmp/ 或 Linear comment |
| 遗漏禁止事项 | 模板中明确列出禁止项 |

---

## 十二、MVP

### 12.1 最小可用版本

普通开发任务模板的 MVP 包含以下最小集合：

| 元素 | 状态 | 说明 |
|------|------|------|
| Title 格式 | ✅ | `type(scope): description` |
| Description 模板 | ✅ | 上下文 + 目标 + write_scope + 禁止项 + Git 约定 + 验收 + 交付物 |
| CI Gate | ✅ | 所有代码任务必须 CI 通过 |
| Git 约定 | ✅ | branch-2 隔离 + merge 流程 |
| 证据要求 | ✅ | CI 状态 + 测试输出 + commit SHA |
| GitHub Push 禁止 | ✅ | 100% 禁止 |
| 回滚策略 | ✅ | revert 流程 |
| Labels | ✅ | `dev-task` + 分类标签 |

### 12.2 MVP 不包含

| 元素 | 说明 |
|------|------|
| 自定义字段 | 需要 Linear 团队先配置 custom fields |
| 自动化 workflow | 需要后续配置 Linear Automations |
| Webhook/Supabase 证据 | 仅在特定任务类型中要求 |
| GitHub Push Gate | 仅在发布/同步任务中要求 |
| Sub-issues 模板 | 后续迭代添加 |

---

## 十三、Linear Markdown 模板（最终产出）

> 以下是可直接粘贴到 Linear Issue Description 中的模板。
> `[...]` 标记需要填写的内容，`[ ]` 标记需要勾选的验收项。

```markdown
## 上下文
[2-3 句话说明任务的背景、为什么做、与哪些已有文件/模块相关]

## 当前状态依据
- 本地 task-list: [引用相关 task list 条目，如无留空]
- CE: [CE Issue 编号，如无留空]
- 代码/测试现场: [关键文件或当前测试结果]

## 目标
1. [具体目标 1]
2. [具体目标 2]

## 修改范围 (write_scope)
- [允许修改的文件/目录/模块，用相对路径]

## 禁止事项
- [明确禁止的操作，例如：禁止改配置、禁止动数据库、禁止触碰 X 文件]

## Git 操作约定
- 从 `branch-1` 创建临时 `branch-2` 分支
- 所有代码工作必须在 `branch-2` 上完成
- 完成后执行: scoped `git add` → commit on `branch-2` → merge into `branch-1` → push `branch-1` to `origin/main` → 写 commit SHA 到证据区
- **100% 禁止直接推送 GitHub**

## 最小验证
- [ ] 运行测试命令: `[具体 pytest 或其他测试命令]`
- [ ] 运行 lint/typecheck: `[具体命令]`
- [ ] 通过标准: [如 `0 failures, 0 warnings`]

## 验收标准
- [ ] **GitLab CI Pipeline 全部通过（硬性前置，不得跳过）**
- [ ] 本地测试通过
- [ ] 无新增 warning
- [ ] 所有修改在 write_scope 范围内
- [ ] 未触碰禁止项
- [ ] branch-2 已正确合并到 branch-1
- [ ] **未直接推送 GitHub**

## 回滚策略
- **触发条件**: CI 失败且无法修复 / 引入回归错误 / 生产异常
- **操作**: 在 branch-1 上 revert merge commit → 验证测试通过 → 更新 Issue 状态 → 记录原因
- **约束**: 已推送 GitLab 的 commit 必须 revert，不得 force push

## 交付物
- [列出期望的文件变更、测试、文档]

## 证据区（完成后填写）
- GitLab CI Pipeline URL: [填写]
- 本地测试输出: [填写]
- Commit SHA (branch-2): [填写]
- 修改文件列表: `git diff --name-only branch-1..branch-2` → [填写]
- Merge commit SHA: [填写]

## 备注
[其他说明]
```

---

**文档状态**：设计完成，待主代理审核  
**下次评审日期**：待定
