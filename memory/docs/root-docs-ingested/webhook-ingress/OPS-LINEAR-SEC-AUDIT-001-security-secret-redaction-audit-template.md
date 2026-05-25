# OPS-LINEAR-SEC-AUDIT-001 安全 / Secret / 脱敏审计模板

> 文档编号：OPS-LINEAR-SEC-AUDIT-001  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  
> 状态：Template（执行时填写）  
> 类型：Security / Secret / Redaction Audit — Linear Issue Template

---

## 一、为什么独立（Why This Is a Separate Audit）

安全 / Secret / 脱敏审计 **必须作为独立的 Linear Issue 类别**，原因如下：

1. **风险性质不同**：secret 泄漏、签名绕过、日志明文等问题的影响是 **不可逆的**。普通 bug 可以后续修复，但已泄漏的 secret 必须强制轮换，代价远高于功能修复。
2. **验收门槛不同**：安全审计任务 **必须** 包含 secret/redaction scan，这是功能开发任务不需要的强制项。
3. **证据链要求不同**：安全审计的证据必须 **证明没有泄漏**（负向证明），而非证明功能正常（正向证明）。
4. **回滚路径不同**：安全审计可能需要紧急密钥轮换、端点下线、日志清理，这些不在普通任务回滚范围内。
5. **CI 阻断机制不同**：任何涉及代码变更的安全审计，GitLab CI 失败时 **绝对禁止合并**，无论其他测试是否通过。
6. **合规要求**：安全审计记录需要作为合规审计的一部分，必须在 Linear 中有独立的、可追溯的 Issue 类型。

**结论**：安全 / Secret / 脱敏审计不能作为普通 Task 或 Bug 的子项，必须作为独立的 Issue 类型，拥有独立的字段、验收标准和证据要求。

---

## 二、适用范围（Applicable / Not Applicable）

### 2.1 适用场景（适用）

| 场景 | 说明 | 示例 |
|------|------|------|
| Secret 泄漏排查 | 代码、日志、数据库、Git 历史中发现或怀疑有明文 secret | OPS-LINEAR-005 中 `raw_headers` 含 `X-Linear-Signature` 明文 |
| 脱敏规则变更 | 修改、新增、删除脱敏逻辑 | 新增 `redaction.py` 中的敏感 key 模式 |
| 签名校验修复 | webhook 签名校验逻辑的 bug 或绕过 | HMAC 校验缺失、timing attack |
| Secret 轮换执行 | 按计划或紧急轮换 webhook secret、API token | 季度轮换、泄漏后紧急轮换 |
| 日志脱敏验证 | 验证日志系统是否仍有明文敏感信息 | Supabase 日志、n8n execution log |
| 安全架构变更 | 修改 DMZ 边界、WAF 规则、防火墙策略 | 新增 webhook 端点、修改 nginx 配置 |
| 凭证存储加固 | 修改 secret 存储方式（环境变量 → KMS） | n8n 凭据加密增强 |

### 2.2 不适用场景（不适用）

| 场景 | 说明 | 原因 |
|------|------|------|
| 纯功能 bug 修复 | 不涉及 secret、脱敏、签名的功能缺陷 | 走普通 Bug 流程即可 |
| 文档更新 | 不涉及安全逻辑的文档修改 | 安全审计模板不适用 |
| 性能优化 | 不涉及安全边界的性能改进 | 走普通 Task 流程 |
| UI/UX 改进 | 前端展示、交互优化 | 不接触 secret |
| 重构（不涉及 secret） | 代码结构调整，不改变安全行为 | 除非影响脱敏逻辑 |

**判断原则**：如果任务 **涉及 secret、签名、脱敏、认证、加密、权限** 中的任何一项，则必须使用此安全审计模板。

---

## 三、Linear Issue 字段定义

### 3.1 必填字段（Required）

| 字段 | 类型 | 说明 | 填写时机 |
|------|------|------|---------|
| `Title` | 文本 | 格式：`SEC-AUDIT-XXX: <简短描述>` | 创建时 |
| `Description` | Markdown | 使用本文档的模板正文 | 创建时 |
| `Team` | 选择 | 关联团队（如 JTO / INFRA） | 创建时 |
| `Labels` | 多选 | 必须包含 `security`、`audit`、`secret` | 创建时 |
| `Priority` | 选择 | 按泄漏等级（见 §5.1） | 创建时 |
| `Status` | 状态 | `Backlog` → `In Progress` → `In Review` → `Done` | 全生命周期 |
| `Assignee` | 选择 | 安全审计执行人 | 创建时或分配时 |
| `Secret/Redaction Scan Required` | Custom Field (Boolean) | **必须为 true** | 创建时（硬规则） |
| `GitLab CI Required` | Custom Field (Boolean) | 涉及代码变更时为 true | 创建时 |
| `GitHub Push Allowed` | Custom Field (Boolean) | **必须为 false** | 创建时（硬规则） |

### 3.2 可选字段（Optional）

| 字段 | 类型 | 说明 |
|------|------|------|
| `Estimate` | 数字 | 预估工作量（点数） |
| `Due Date` | 日期 | 安全审计截止时间 |
| `Related Issues` | 关联 | 关联的功能 Issue 或父 Issue |
| `External Links` | URL | 关联的 GitLab MR、n8n workflow、Supabase dashboard |
| `Attachment` | 文件 | 脱敏后的证据截图、日志片段（确保无明文 secret） |
| `Incident ID` | 文本 | 如果是紧急泄漏事件，关联事故编号 |

### 3.3 自定义字段（Custom Fields — Linear Admin 需配置）

| 字段名 | 类型 | 选项 / 默认值 | 说明 |
|--------|------|-------------|------|
| `Audit Category` | Dropdown | `secret_leak` / `redaction_fix` / `signature_repair` / `rotation` / `log_verification` / `architecture_change` / `credential_hardening` | 审计类别 |
| `Leak Severity` | Dropdown | `critical` / `high` / `medium` / `low` / `preventive` | 泄漏严重程度 |
| `Secret Scan Result` | Dropdown | `pending` / `passed` / `failed` / `not_applicable` | secret scan 结果 |
| `CI Status` | Dropdown | `not_required` / `pending` / `passed` / `failed` | GitLab CI 状态 |
| `Evidence Attached` | Boolean | `false` | 是否已附加证据 |

---

## 四、验收标准（Acceptance Criteria）

### 4.1 硬性验收标准（必须全部通过）

| # | 验收项 | 验证方式 | 通过条件 |
|---|--------|---------|---------|
| AC-1 | Secret scan 已执行 | 运行 secret scan 工具（如 gitleaks、trufflehog、自定义脚本） | scan 结果 = `passed`，无明文 secret 残留 |
| AC-2 | 脱敏逻辑已验证 | 检查日志、数据库、缓存中的敏感字段 | 所有敏感字段 = `[REDACTED]` 或等效脱敏 |
| AC-3 | GitLab CI 通过 | CI pipeline 全部 job 成功 | 所有 job = `passed` |
| AC-4 | GitHub 无直接 push | 检查 Git 历史、GitHub 仓库 | 无直接 push 记录，所有变更通过 GitLab CI 合并 |
| AC-5 | 证据中无 secret 原文 | 审查所有证据附件、日志片段 | 证据中无任何明文 secret、token、password |
| AC-6 | 回滚预案已准备 | 文档中明确回滚步骤 | 回滚步骤可执行、已测试 |
| AC-7 | Secret 已轮换（如泄漏） | 检查 secret 版本和轮换记录 | 旧 secret 已失效，新 secret 已生效 |

### 4.2 软性验收标准（建议通过）

| # | 验收项 | 说明 |
|---|--------|------|
| AC-8 | 日志保留策略已审查 | 确认敏感日志的保留期限符合合规要求 |
| AC-9 | 权限审查已完成 | 确认只有必要人员有 secret 访问权限 |
| AC-10 | 监控告警已配置 | secret 泄漏、签名失败有自动告警 |

---

## 五、证据要求（Evidence Requirements）

### 5.1 必须提供的证据

| 证据编号 | 证据类型 | 内容 | 脱敏要求 | 存放位置 |
|---------|---------|------|---------|---------|
| EV-1 | Secret scan 报告 | scan 工具输出结果（JSON/TXT） | 报告中不得包含实际 secret 值 | `memory/evidence/SEC-AUDIT-XXX/scan-report.txt` |
| EV-2 | 脱敏验证查询结果 | SQL 查询或日志 grep 结果 | 查询结果中敏感字段必须显示为 `[REDACTED]` | `memory/evidence/SEC-AUDIT-XXX/redaction-verification.txt` |
| EV-3 | GitLab CI 截图/日志 | CI pipeline 执行记录 | 日志中无明文 secret | CI 系统或本地保存 |
| EV-4 | Git 历史审查 | `git log --oneline` + `git diff` | diff 中无新增 secret | `memory/evidence/SEC-AUDIT-XXX/git-review.txt` |
| EV-5 | 回滚测试记录 | 回滚步骤执行截图/日志 | 如涉及 secret，使用占位符 | `memory/evidence/SEC-AUDIT-XXX/rollback-test.txt` |

### 5.2 证据脱敏规则（强制）

1. **禁止** 在任何证据文件中出现明文 secret、token、password、API key。
2. **所有** 敏感值必须替换为 `[REDACTED]` 或 `sk-[REDACTED]`。
3. **邮箱** 脱敏为 `a***@d***.com` 格式。
4. **IP 地址** 可保留（用于溯源），但不与 secret 同时出现。
5. **签名值** 必须完全脱敏，即使已过期。
6. **数据库连接字符串** 脱敏为 `postgresql://[REDACTED]:[REDACTED]@[REDACTED]/[REDACTED]`。

### 5.3 证据审查流程

```
执行人收集证据
    │
    ▼
执行自审（检查是否有明文 secret）
    │
    ▼
提交给审核人
    │
    ▼
审核人二次审查（独立检查是否有明文 secret）
    │
    ├── 有明文 secret → 退回，要求重新脱敏
    │
    └── 无明文 secret → 通过，附加到 Linear Issue
```

---

## 六、CI 要求（Whether CI Is Required）

| 条件 | CI 要求 | 说明 |
|------|---------|------|
| **涉及代码变更** | **必须 GitLab CI 成功** | 任何 .py / .ts / .js / .yaml / .conf 变更都需 CI |
| **仅文档变更** | CI 不要求（但建议运行 lint） | Markdown 文档更新不需要 CI 阻断 |
| **配置变更** | **必须 GitLab CI 成功** | nginx conf、docker-compose、env 模板变更 |
| **紧急 hotfix** | **必须 GitLab CI 成功** | 即使是紧急修复，也不允许跳过 CI |

**硬规则**：
- 任何涉及代码或配置变更的安全审计任务，**GitLab CI 必须全部 job 成功**，否则不得合并。
- CI 失败时，不得通过 `--force` 或管理员权限绕过。
- CI pipeline 中 **必须** 包含 secret scan step（如 gitleaks、自定义 redaction check）。

---

## 七、GitHub Push 政策（Whether GitHub Push Is Allowed）

### 7.1 规则

| 操作 | 是否允许 | 说明 |
|------|---------|------|
| GitHub 直接 push | **100% 禁止** | 安全审计任务 **绝对禁止** 直接 push 到 GitHub |
| GitLab MR 合并 | 允许（经 CI 和审查） | 所有变更必须通过 GitLab MR 流程 |
| GitHub PR 创建 | 允许（仅镜像） | 如果是 GitLab → GitHub 镜像流程，允许 |
| GitHub force push | **100% 禁止** | 任何情况都不允许 force push 到 GitHub |

### 7.2 禁止原因

1. 安全审计涉及敏感信息，GitHub 直接 push 跳过 CI secret scan。
2. GitHub 仓库可能有更多可见性，增加泄漏风险。
3. GitLab CI 包含安全扫描步骤，GitHub 直推绕过这些检查。
4. 合规要求所有安全相关变更必须经过 CI + 审查流程。

---

## 八、Push 前置条件（Preconditions for Push/Merge）

在执行任何 push 或 merge 操作之前，**必须** 确认以下所有条件：

| # | 前置条件 | 验证方式 | 状态 |
|---|---------|---------|------|
| PC-1 | Secret scan 通过 | scan 报告无明文 secret | [ ] |
| PC-2 | 脱敏逻辑验证通过 | 测试数据经脱敏后无明文 | [ ] |
| PC-3 | GitLab CI 全部通过 | pipeline 所有 job = `passed` | [ ] |
| PC-4 | 至少 1 人代码审查通过 | GitLab MR 有 approved review | [ ] |
| PC-5 | 证据中无 secret 原文 | 独立审查所有证据文件 | [ ] |
| PC-6 | 回滚预案已就绪 | 回滚步骤已文档化并可执行 | [ ] |
| PC-7 | 变更范围已确认 | `git diff --stat` 仅包含预期变更 | [ ] |
| PC-8 | 无未解决的 security findings | 所有 CI 安全扫描警告已处理 | [ ] |

**如果任何一项未满足，不得执行 push 或 merge。**

---

## 九、Webhook / Supabase / n8n 证据需求

### 9.1 Webhook 证据

| 证据项 | 验证方式 | 通过条件 |
|--------|---------|---------|
| Webhook secret 已配置 | `docker exec <container> env | grep LINEAR_WEBHOOK_SECRET` | 返回 `EXISTS`，不显示值 |
| 签名校验有效 | 发送带正确签名的测试事件 | HTTP 200, status=`accepted` |
| 签名校验拒绝伪造 | 发送带错误签名的测试事件 | HTTP 401/403 |
| Webhook 端点最小化 | nginx 配置审查 | 仅 `/webhook/linear` 可达 |

### 9.2 Supabase 证据

| 证据项 | 验证 SQL | 通过条件 |
|--------|---------|---------|
| `raw_headers` 脱敏 | 见 §10.2 | 所有敏感 key 的值 = `[REDACTED]` |
| 无明文 secret 在数据库中 | 全表扫描敏感模式 | 0 行匹配明文 secret |
| RLS 策略生效 | 使用 non-service_role 连接 | 拒绝写入 |
| 日志表无敏感信息 | `webhook_processing_logs` 审查 | 无明文 secret/token |

**脱敏验证 SQL**：

```sql
-- 检查 raw_headers 中是否有未脱敏的签名值
SELECT event_id, raw_headers
FROM webhook_raw_events
WHERE provider = 'linear'
  AND (
    raw_headers->>'x-linear-signature' NOT IN ('[REDACTED]', null)
    OR raw_headers->>'X-Linear-Signature' NOT IN ('[REDACTED]', null)
    OR raw_headers->>'authorization' NOT IN ('[REDACTED]', null)
    OR raw_headers->>'Authorization' NOT IN ('[REDACTED]', null)
  )
  AND created_at > NOW() - INTERVAL '24 hours';
-- 预期结果: 0 行
```

### 9.3 n8n 证据

| 证据项 | 验证方式 | 通过条件 |
|--------|---------|---------|
| n8n 凭据库加密 | 检查 `N8N_ENCRYPTION_KEY` 已设置 | 环境变量存在且非默认值 |
| n8n execution log 无明文 | 审查最近 execution 的 input/output | 无明文 secret |
| n8n 后台不暴露公网 | 从公网访问 n8n 端口 | 连接拒绝/超时 |

---

## 十、回滚需求（Rollback Requirements）

### 10.1 回滚触发条件

| 条件 | 说明 |
|------|------|
| Secret scan 发现新的泄漏 | 变更后反而暴露了更多 secret |
| 脱敏逻辑破坏正常功能 | 脱敏规则过于激进，过滤了正常数据 |
| 签名校验阻止了合法请求 | 签名校验逻辑有误，拒绝合法 webhook |
| CI 反复失败无法修复 | 超过 3 次 CI 失败，需要回退到已知安全状态 |

### 10.2 回滚步骤模板

```bash
# 1. 回滚 Git 变更
git revert <commit-sha> --no-edit

# 2. 重新部署上一个已知安全的版本
docker compose up -d --force-recreate  # 或使用 kubectl rollout undo

# 3. 确认回滚后服务正常
curl -sf https://webhook.exa.edu.kg/health

# 4. 重新验证脱敏（回滚后必须再次确认）
# 运行 EV-2 脱敏验证查询

# 5. 记录回滚原因和时间
echo "Rollback at $(date -u +%Y-%m-%dT%H:%M:%SZ): <reason>" >> rollback.log
```

### 10.3 紧急回滚（Secret 已泄漏）

```bash
# 1. 立即轮换泄漏的 secret
#    - Linear: 在 Settings > Webhooks 中重新生成 secret
#    - n8n: 更新环境变量 LINEAR_WEBHOOK_SECRET
#    - 重启相关服务使新 secret 生效

# 2. 下线受影响端点（如必要）
#    docker stop webhook-ingress

# 3. 清理可能泄漏的日志
#    按日志保留策略，删除包含明文 secret 的日志段

# 4. 通知相关人员
#    安全事件通报（不通过公开渠道发送新 secret）

# 5. 事后审计
#    创建新的 SEC-AUDIT Issue 记录泄漏原因和修复过程
```

---

## 十一、Factory 子代理需求（Factory Subagent Requirements）

### 11.1 子代理分工

| 子代理角色 | 职责 | 输入 | 输出 |
|-----------|------|------|------|
| `bailian-worker` | 主编码、安全扫描脚本、脱敏逻辑实现 | 安全需求描述 | 代码变更 + 扫描报告 |
| `qa-bot` | 安全审计验收测试、脱敏验证 | 变更后的代码 | 验收测试报告 |
| `doc-bot` | 审计文档编写、证据整理 | 技术变更内容 | 文档更新 + 证据归档 |

### 11.2 子代理协作流程

```
main-thread 分发 SEC-AUDIT 任务
    │
    ├── bailian-worker: 执行安全扫描、修复脱敏逻辑
    │       │
    │       ▼
    │   提交代码变更 → GitLab CI 自动触发
    │       │
    │       ├── CI secret scan
    │       ├── 单元测试
    │       └── 集成测试
    │
    ├── qa-bot: 执行安全验收测试
    │       │
    │       ├── AC-1: Secret scan 验证
    │       ├── AC-2: 脱敏验证
    │       └── AC-5: 证据审查
    │
    └── doc-bot: 整理审计文档和证据
            │
            ├── 编写 Linear Issue 描述
            ├── 整理证据附件（已脱敏）
            └── 更新关联文档
```

### 11.3 子代理安全约束

1. **所有子代理** 不得在输出中包含明文 secret。
2. **bailian-worker** 执行的安全扫描工具不得将扫描结果上传到外部服务。
3. **qa-bot** 的测试不得向生产环境发送真实 secret。
4. **doc-bot** 整理证据时必须执行脱敏审查。

---

## 十二、风险矩阵（Risk Matrix）

| 风险 | 可能性 | 影响 | 缓解措施 | 残余风险 |
|------|--------|------|----------|----------|
| Secret 在代码审查中泄漏 | 低 | 极高 | CI secret scan + 双人审查 | 极低 |
| 脱敏规则漏掉新的敏感字段 | 中 | 高 | 定期审查脱敏模式列表 + 自动测试 | 低 |
| 回滚失败导致服务中断 | 低 | 高 | 回滚前测试 + 蓝绿部署 | 低 |
| 证据文件本身包含 secret | 中 | 极高 | 证据脱敏审查流程（双重检查） | 低 |
| GitHub 误操作直接 push | 低 | 极高 | 分支保护规则 + CI 强制检查 | 极低 |
| 子代理输出包含 secret | 低 | 高 | 子代理输出过滤 + 人工审查 | 低 |
| CI secret scan 工具漏报 | 低 | 高 | 多工具交叉扫描（gitleaks + trufflehog + 自定义） | 低 |

---

## 十三、MVP（Minimum Viable Process）

最小可行的安全审计流程，适用于初次实施：

### 13.1 MVP 步骤

| 步骤 | 操作 | 工具/方式 | 时间 |
|------|------|----------|------|
| 1 | 创建 Linear SEC-AUDIT Issue | Linear UI，使用本模板 | 5 min |
| 2 | 运行 secret scan | `gitleaks detect --source .` 或自定义脚本 | 5 min |
| 3 | 检查日志和数据库脱敏 | SQL 查询 + 日志 grep | 10 min |
| 4 | 确认 GitLab CI 通过 | CI pipeline 检查 | 等待 CI |
| 5 | 审查证据文件 | 人工检查无明文 secret | 5 min |
| 6 | 填写 Linear Issue 验收标准 | 更新 AC 表格 | 5 min |
| 7 | 关闭 Issue | Linear UI | 2 min |

**总时间**：约 30 分钟（不含 CI 等待时间）

### 13.2 MVP 与完整流程的差异

| 项目 | MVP | 完整流程 |
|------|-----|---------|
| Secret scan 工具 | 单一工具（gitleaks） | 多工具交叉扫描 |
| 脱敏验证范围 | 仅直接相关字段 | 全表扫描 + 历史日志 |
| 代码审查 | 单人 | 双人 + 安全专家 |
| 回滚测试 | 文档化但不执行 | 实际执行回滚测试 |
| 证据归档 | 本地文件 | 独立证据目录 + Linear 附件 |
| 子代理参与 | 仅 bailian-worker | bailian-worker + qa-bot + doc-bot |

---

## 十四、Linear Markdown 模板（可直接复制使用）

以下是可直接粘贴到 Linear Issue Description 的模板：

```markdown
# SEC-AUDIT: [简短描述]

> Audit Category: [secret_leak / redaction_fix / signature_repair / rotation / log_verification / architecture_change / credential_hardening]
> Leak Severity: [critical / high / medium / low / preventive]

---

## 问题描述

[描述安全问题的具体内容、影响范围、发现途径]

## 影响范围

- 受影响系统: [列出]
- 受影响 secret 类型: [列出，使用 [REDACTED] 替代实际值]
- 受影响用户: [内部 / 外部 / 无]
- 时间范围: [从何时到何时]

## 根因分析

[描述导致此安全问题的根本原因]

## 修复方案

[描述计划采取的修复措施]

## 验收标准

- [ ] AC-1: Secret scan 已执行并通过
- [ ] AC-2: 脱敏逻辑已验证
- [ ] AC-3: GitLab CI 全部通过
- [ ] AC-4: GitHub 无直接 push
- [ ] AC-5: 证据中无 secret 原文
- [ ] AC-6: 回滚预案已准备
- [ ] AC-7: Secret 已轮换（如适用）

## 证据清单

- [ ] EV-1: Secret scan 报告
- [ ] EV-2: 脱敏验证查询结果
- [ ] EV-3: GitLab CI 截图/日志
- [ ] EV-4: Git 历史审查
- [ ] EV-5: 回滚测试记录

## Push 前置条件

- [ ] PC-1: Secret scan 通过
- [ ] PC-2: 脱敏逻辑验证通过
- [ ] PC-3: GitLab CI 全部通过
- [ ] PC-4: 至少 1 人代码审查通过
- [ ] PC-5: 证据中无 secret 原文
- [ ] PC-6: 回滚预案已就绪
- [ ] PC-7: 变更范围已确认
- [ ] PC-8: 无未解决的 security findings

## 回滚预案

[描述回滚步骤和触发条件]

## 关联 Issue / MR

- GitLab MR: [链接]
- 关联功能 Issue: [链接]
- 父 Issue: [如有]

## 执行记录

| 时间 | 操作 | 执行人 | 备注 |
|------|------|--------|------|
| [ISO 8601] | [操作] | [人] | [备注] |

## 最终结论

[审计通过 / 有条件通过 / 不通过]

[总结性说明]
```

---

## 十五、附录

### 15.1 关联文档

| 文档编号 | 文档名称 | 关系 |
|----------|----------|------|
| SEC-ARCH-001 | Linear Webhook + n8n 安全架构方案 | 安全架构基准 |
| OPS-LINEAR-005 | Shadow Validation Report | 包含实际脱敏修复案例 |
| OPS-LINEAR-006 | Dry-Run Acceptance Report Template | 包含脱敏验收项 |
| `tools/webhook_ingress/redaction.py` | 脱敏逻辑实现 | 代码级脱敏参考 |

### 15.2 常用脱敏验证命令

```bash
# 1. 检查代码中是否有硬编码 secret
git grep -iE '(password|secret|token|api_key|authorization)\s*[:=]\s*["\x27][^"\x27]+["\x27]' -- '*.py' '*.ts' '*.js' '*.yaml' '*.yml' '*.conf'

# 2. 检查 git 历史中是否有 secret（不输出实际值）
git log -p --all | grep -iE '(password|secret|token|api_key)\s*[:=]' | grep -v '\[REDACTED\]' | grep -v '#.*redacted' | head -20

# 3. 检查日志文件中的敏感模式（示例）
grep -rE '[a-f0-9]{64}|sk-[a-zA-Z0-9]{20,}' /path/to/logs/ --include='*.log' | grep -v '\[REDACTED\]'

# 4. gitleaks 扫描（如有安装）
gitleaks detect --source . --report-path /tmp/gitleaks-report.json --report-format json
```

### 15.3 版本历史

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| V1.0 | 2026-05-04 | 初始版本 | bailian-worker |

---

**文档状态**：已发布（Template）  
**审批人**：待定  
**下次评审日期**：首次使用后 30 天
