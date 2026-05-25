# Linear 生产切流 / 回滚模板

> 文档编号：OPS-TEMPLATE-001  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-07  
> 类型：Linear Issue Template（生产级切流操作）

---

## 一、为什么需要独立模板

生产切流（Production Traffic Switch / Cutover）是 **最高风险** 的运维操作之一，与常规 bug fix、功能开发、dry-run 或 canary 验证有本质区别：

1. **不可逆性窗口**：切流一旦发生，影响真实用户流量和数据；回滚虽可行但有时间窗口约束
2. **多方依赖**：涉及 CI 通过、GitHub Push Gate、Webhook 可达性、Supabase 数据一致性、n8n 工作流活性
3. **证据链要求**：必须有完整的切流前证据（evidence pack）、切流中监控、切流后验收
4. **回滚是默认假设**：任何生产切流必须在方案设计时就包含可执行的一键回滚方案

因此需要独立于常规 Linear Issue 的 **专用模板**，确保每次切流都有统一的结构化审批和执行标准。

---

## 二、适用范围

### 2.1 适用场景

| 场景 | 示例 |
|------|------|
| Webhook URL 切换 | Linear webhook 从 shadow 切换到 production |
| n8n 工作流切换 | 从 `canonical-dryrun-events` 切换到 `production-canary-events` |
| 消费模式切换 | webhook-ingress 模式从 `shadow` → `production_canary` → `production` |
| 外部 core 版本升级 | memory external-core release 版本切换 |
| 路由规则变更 | nginx/gateway 路由配置更新 |

### 2.2 不适用场景

| 场景 | 原因 |
|------|------|
| 纯 dry-run 验证 | 不涉及生产流量，用 dry-run 模板即可 |
| Canary 验证（仅 comment action） | 不影响路由/消费链路，用 canary 验证模板 |
| 文档更新 / 代码重构 | 不涉及运行配置变更 |
| 新建 shadow 基础设施 | 无生产影响，用部署记录模板 |

---

## 三、模板字段定义

### 3.1 必填字段（Required Fields）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| **切流编号** | 文本 | 唯一标识符 | `OPS-LINEAR-XXX` |
| **切流类型** | 枚举 | `webhook_url` / `n8n_workflow` / `ingress_mode` / `core_version` / `route_config` | `ingress_mode` |
| **切流方向** | 文本 | 从什么状态到什么状态 | `production_canary` → `production` |
| **切流窗口** | 时间窗口 | 计划的切流时间段（含时区） | `2026-05-05 02:00-04:00 CST` |
| **负责人** | 文本 | 切流执行人 | `bailian-07` |
| **审批人** | 文本 | 审批此切流的人员 | `main-thread` |
| **目标系统** | 文本 | 被切流的系统/服务 | `webhook-ingress-shadow on node-22` |
| **回滚方案** | 文本/链接 | 指向回滚方案的文档链接 | `OPS-LINEAR-XXX-rollback-plan.md` |
| **Evidence Pack** | 文本/链接 | 切流前证据包文档链接 | `OPS-LINEAR-XXX-evidence-pack.md` |
| **监控指标** | 多行文本 | 切流期间需要监控的关键指标 | 见下方模板 |
| **回滚触发条件** | 多行文本 | 什么条件下必须立即回滚 | 见下方模板 |

### 3.2 可选字段（Optional Fields）

| 字段 | 类型 | 说明 |
|------|------|------|
| **关联 Linear Issue** | 链接 | 关联的变更/开发 Issue |
| **变更 PR/MR 链接** | 链接 | 代码变更的 GitLab/GitHub PR |
| **CI Pipeline 链接** | 链接 | 验证通过的 CI 运行链接 |
| **沟通频道** | 文本 | 切流期间的沟通渠道（如 Slack 频道） |
| **备用负责人** | 文本 | 主负责人不可用时的备份 |
| **切流后观察期** | 时间 | 切流后的额外观察时间 | `+2 小时` |
| **历史切流参考** | 链接 | 之前类似切流的文档 |

### 3.3 自动化门控字段（Gate Fields）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| **CI 要求** | 布尔 | `true` | 涉及代码变更是否要求 CI 通过 |
| **CI 状态** | 枚举 | `not_run` → `running` → `success` / `failed` | 当前 CI 状态 |
| **GitHub Push 允许** | 布尔 | `false` | 是否允许 GitHub 自动 push |
| **GitHub Push 前置条件** | 多行文本 | 见下方模板 | 允许 GitHub push 的前置条件 |
| **Webhook 证据需求** | 多行文本 | 见下方模板 | 切流前必须验证的 Webhook 证据 |
| **Supabase 证据需求** | 多行文本 | 见下方模板 | 切流前必须验证的 Supabase 证据 |
| **n8n 证据需求** | 多行文本 | 见下方模板 | 切流前必须验证的 n8n 证据 |

---

## 四、Linear Markdown 模板（可直接粘贴到 Issue 描述）

```markdown
# 生产切流工单

> 切流编号：[OPS-XXXX]
> 创建日期：[YYYY-MM-DD]
> 状态：`planning` → `evidence_ready` → `approved` → `executing` → `verified` → `completed` | `rolled_back`

---

## 1. 切流概要

| 项目 | 内容 |
|------|------|
| **切流编号** | [OPS-XXXX] |
| **切流类型** | [webhook_url / n8n_workflow / ingress_mode / core_version / route_config] |
| **切流方向** | [当前状态] → [目标状态] |
| **切流窗口** | [YYYY-MM-DD HH:MM-HH:MM TZ] |
| **负责人** | [@username] |
| **审批人** | [@username] |
| **目标系统** | [系统/服务描述] |
| **关联 Issue** | [链接] |
| **关联 PR/MR** | [链接] |

---

## 2. Evidence Pack（切流前证据）

> **硬规则**：没有 Evidence Pack 不得执行切流。

**Evidence Pack 文档**：[链接到 OPS-XXXX-evidence-pack.md]

Evidence Pack 必须包含：

- [ ] **切流前系统快照**：当前配置、模式、路由的完整记录
- [ ] **变更差异对比**：切流前后的配置 diff
- [ ] **CI 通过证明**（如涉及代码）：CI pipeline 链接 + 状态截图
- [ ] **回滚方案验证**：回滚脚本已在测试/预发环境验证通过
- [ ] **无敏感信息泄露**：Evidence Pack 不包含 token、密码、签名密钥

### 2.1 CI 要求

| 项目 | 值 |
|------|-----|
| **是否涉及代码变更** | [是 / 否] |
| **CI 是否必须通过** | [是 / 否] |
| **CI Pipeline 链接** | [链接] |
| **CI 状态** | `success` / `failed` / `not_run` |

> **规则**：涉及代码变更 → CI 必须 `success` → 否则禁止切流。

### 2.2 GitHub Push Gate

| 项目 | 值 |
|------|-----|
| **是否涉及 GitHub 发布/同步** | [是 / 否] |
| **是否允许 GitHub Push** | [是 / 否] |
| **Push 前置条件** | [见下方检查清单] |

**GitHub Push 前置条件清单**：

- [ ] CI pipeline 已成功通过
- [ ] 代码已在目标分支（如 `main` 或 `branch-1`）合并
- [ ] 无未解决的 merge conflict
- [ ] Push 操作已由审批人批准
- [ ] Push 内容不包含敏感信息

> **规则**：未经审批人明确批准，不得执行 GitHub push。

### 2.3 Webhook 证据需求

切流前必须验证的 Webhook 相关证据：

- [ ] Webhook 端点健康检查通过（`GET /health` 返回 `status: ok`）
- [ ] Webhook 签名验证正常（无 401 错误）
- [ ] 当前 Webhook 路由配置已记录（nginx / gateway 配置快照）
- [ ] 目标 Webhook URL 可达（`curl` 测试通过）
- [ ] Webhook 事件类型覆盖完整（至少覆盖 `Issue` / `Comment` 等关键类型）

### 2.4 Supabase 证据需求

切流前必须验证的 Supabase 相关证据：

- [ ] `webhook_raw_events` 表可正常写入和查询
- [ ] `webhook_canonical_events` 表可正常写入和查询
- [ ] `webhook_processing_logs` 表可正常写入和查询
- [ ] 最近 N 条事件处理无错误（查询 `level != 'ERROR'`）
- [ ] 数据库连接池状态正常
- [ ] 关键索引存在（`event_id`、`idempotency_key`、`delivery_id`）

### 2.5 n8n 证据需求

切流前必须验证的 n8n 相关证据：

- [ ] 目标 n8n workflow 状态为 `active`
- [ ] 最近 N 次 execution 状态均为 `success`
- [ ] n8n 容器健康状态正常
- [ ] n8n webhook URL 可从 webhook-ingress 容器内访问
- [ ] 如有 canary action，验证其开关状态符合预期

---

## 3. 切流执行方案

### 3.1 执行步骤

| 步骤 | 操作 | 命令/操作 | 预期结果 |
|------|------|-----------|----------|
| 1 | 备份当前配置 | [命令] | 备份文件已创建 |
| 2 | 执行切流操作 | [命令] | 配置已更新 |
| 3 | 重启相关服务 | [命令] | 服务重启成功 |
| 4 | 验证切流结果 | [验证命令] | 验证通过 |

### 3.2 切流时间线

```
T+00:00  — 开始切流窗口
T+00:05  — 步骤 1: 备份
T+00:10  — 步骤 2: 执行切流
T+00:15  — 步骤 3: 重启服务
T+00:20  — 步骤 4: 验证切流结果
T+00:30  — 监控确认稳定
T+00:60  — 切流窗口结束 / 进入观察期
```

---

## 4. 监控

### 4.1 切流期间监控指标

| 指标 | 正常范围 | 告警阈值 | 监控方式 |
|------|----------|----------|----------|
| HTTP 5xx 错误率 | < 0.1% | > 1% | nginx access log |
| Webhook 401 错误数 | 0 | > 5 | webhook-ingress logs |
| Supabase 写入延迟 | < 100ms | > 1s | processing_logs timestamp |
| n8n execution 失败率 | 0% | > 0% | n8n execution_entity |
| 服务响应时间（p99） | < 500ms | > 2s | health endpoint |

### 4.2 回滚触发条件

满足以下 **任一** 条件即触发回滚：

| 条件 | 严重级别 | 动作 |
|------|----------|------|
| HTTP 5xx 错误率 > 5% 持续 2 分钟 | Critical | 立即回滚 |
| Webhook 签名验证连续失败 > 10 次 | Critical | 立即回滚 |
| Supabase 写入失败 > 5 次 | High | 回滚 |
| n8n workflow 执行连续失败 > 3 次 | High | 回滚 |
| 服务无法启动或健康检查失败 | Critical | 立即回滚 |
| 发现安全漏洞/敏感信息泄露 | Critical | 立即回滚 + 安全审计 |
| 业务功能异常（用户报告） | High | 评估后回滚 |

---

## 5. 回滚方案

> **硬规则**：没有回滚方案不得执行切流。

**回滚方案文档**：[链接到 OPS-XXXX-rollback-plan.md]

### 5.1 一键回滚命令

```bash
# 回滚命令模板（根据实际切流类型填充）
ssh root@node-22 'set -euo pipefail
cd /opt/n8n-linear

# Step 0: 备份当前 .env
TS=$(date +%Y%m%d-%H%M%S)
cp .env ".env.bak-rollback-${TS}"

# Step 1: 恢复到切流前的配置
# [根据具体切流类型填写]

# Step 2: 重启相关服务
docker compose up -d --force-recreate webhook-ingress

# Step 3: 验证回滚结果
sleep 5
docker exec webhook-ingress-shadow python3 -c "
# 验证回滚后模式正确
print(\"rollback_ok\")
"

echo "=== ROLLBACK COMPLETE ==="
'
```

### 5.2 回滚验证

回滚后必须验证：

- [ ] 系统恢复到切流前状态
- [ ] 所有核心功能正常运行
- [ ] 数据一致性（无丢失或损坏）
- [ ] 监控指标恢复正常
- [ ] 旧配置/旧版本仍可用（如适用）

---

## 6. Factory 子代理需求

| 项目 | 内容 |
|------|------|
| **是否需要 Factory 子代理** | [是 / 否] |
| **需要哪些子代理** | [如：bailian-07（执行）、qa-bot（验证）、dev-bot（代码变更）] |
| **子代理分工** | [见下方] |
| **主代理** | [main-thread 或其他] |

### 6.1 子代理分工（如需要）

| 子代理 | 职责 | 输出物 |
|--------|------|--------|
| [bailian-07] | [切流执行] | [切流报告] |
| [qa-bot] | [回滚验证] | [验证报告] |
| [dev-bot] | [代码变更] | [PR/MR + CI 结果] |

---

## 7. 风险分析

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| [风险描述] | [高/中/低] | [高/中/低] | [缓解方案] |

---

## 8. 验收标准

| 编号 | 标准 | 验证方式 | 状态 |
|------|------|----------|------|
| P0-CUT-01 | Evidence Pack 完整且通过审核 | 人工审核 | `[ ]` |
| P0-CUT-02 | 回滚方案已验证通过 | 回滚脚本测试 | `[ ]` |
| P0-CUT-03 | CI 通过（如适用） | CI pipeline 截图 | `[ ]` |
| P0-CUT-04 | GitHub Push Gate 通过（如适用） | Push 审批记录 | `[ ]` |
| P0-CUT-05 | 切流执行成功 | 切流后验证命令 | `[ ]` |
| P0-CUT-06 | 监控指标正常 | 监控截图/数据 | `[ ]` |
| P0-CUT-07 | 切流后观察期无异常 | 观察期日志 | `[ ]` |
| P0-CUT-08 | 无敏感信息泄露 | 日志审计 | `[ ]` |

---

## 9. 切流后归档

### 9.1 归档文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 切流方案 | `docs/webhook-ingress/OPS-XXXX-cutover-plan.md` | 本工单关联的详细方案 |
| Evidence Pack | `docs/webhook-ingress/OPS-XXXX-evidence-pack.md` | 切流前证据 |
| 回滚方案 | `docs/webhook-ingress/OPS-XXXX-rollback-plan.md` | 回滚预案 |
| 验收报告 | `docs/webhook-ingress/OPS-XXXX-acceptance-report.md` | 切流后验收 |

### 9.2 归档检查

- [ ] 所有文件已存入 `docs/webhook-ingress/` 目录
- [ ] Git 提交已推送（如适用）
- [ ] Linear Issue 状态更新为 `Completed`
- [ ] 切流经验已记录（如有教训）

---

## 10. 与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-TEMPLATE-001 模板 | OPS-LINEAR-005 shadow validation | 本文模板化 005 的切流验证模式 |
| OPS-TEMPLATE-001 模板 | OPS-LINEAR-008 rollback plan | 本文模板化 008 的回滚方案模式 |
| OPS-TEMPLATE-001 模板 | OPS-LINEAR-011 evidence pack | 本文模板化 011 的证据包模式 |

---

**文档状态**：模板  
**下次评审**：首次实际切流使用后评审
```

---

## 五、MVP 实施建议

### 5.1 MVP 范围

第一版模板仅覆盖最核心的字段和流程：

1. **切流概要表**：编号、类型、方向、窗口、负责人、审批人
2. **Evidence Pack 清单**：5 个核心检查项（系统快照、配置 diff、CI、回滚验证、无敏感信息）
3. **执行步骤表**：4 步标准流程（备份 → 执行 → 重启 → 验证）
4. **回滚触发条件**：6 个关键触发条件
5. **验收标准**：8 个 P0 检查项

### 5.2 后续迭代

| 版本 | 新增内容 |
|------|----------|
| V1.1 | 增加自动化 CI/CD 集成字段 |
| V1.2 | 增加多系统联动切流支持 |
| V2.0 | 增加基于 Linear 自定义字段的结构化表单 |

---

## 六、注意事项

1. **本模板不修改任何生产配置**：仅作为 Linear Issue 的描述模板，用于规范切流工单的结构和内容
2. **实际切流命令需根据场景填写**：模板中的命令是示例，实际执行需根据具体切流类型调整
3. **Evidence Pack 和回滚方案是硬性要求**：两者缺一不可，否则不得批准切流
4. **CI 通过是代码变更的前置条件**：涉及代码的切流必须等待 GitLab CI success
5. **GitHub Push Gate 是发布的前置条件**：涉及 GitHub 发布/同步的切流必须经过审批

---

**文档状态**：V1.0 草稿  
**审批人**：待定  
**首次使用场景**：下一次生产切流操作
