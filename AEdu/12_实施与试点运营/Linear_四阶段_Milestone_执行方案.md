# AEdu Linear 四阶段 Project Milestones 执行方案

> 文档编号：OPS-LINEAR-001
> 版本：V1.0
> 创建日期：2026-05-03
> 维护人：bailian-worker

---

## 一、方案摘要

本方案为 AEdu（课课·教育孪生项目）在 Linear 上建立四阶段 Project Milestones 执行方案。
四阶段按照 AEdu 架构的分层演进顺序设计，与 `CLAUDE-001` 中定义的项目方法论完全一致。

**核心约束**：本方案仅输出执行方案与风险分析，**不对 Linear 进行任何实际写入操作**。

---

## 二、四阶段 Milestone 定义

### 阶段一：最小闭环验证期（Phase 1: Minimum Closed-Loop Validation）

| 属性 | 值 |
|------|------|
| **Linear Milestone name** | `M1 - 最小闭环验证期` |
| **对应 AEdu 架构层** | 01 战略与总纲 → 02 知识底座 → 05 学生数字孪生 → 06 数据接入 → 08 观察层（最小子集） |
| **核心目标** | 跑通"数据输入 → 学生状态建模 → 简单观察输出"的最小端到端闭环 |
| **验证标准** | 1 个学科（高中物理）+ 1 个学生孪生 + 1 种数据源（微信/手动录入）→ 输出家长端可阅读的观察报告 |

**关键交付物**：
- 固定知识底座最小可用版本（KB-001，1 学科）
- StudentTwinAgent 核心字段与状态模型（TWIN-001/002/003）
- 学习事件生成标准最小集（INGEST-007 子集）
- 图谱记忆层最小可用版本（GRAPH-001 子集）
- 前台观察层 MVP（OBS-001 子集）

**对应 Linear Issues 建议**（示例命名，非实际创建）：
| Issue 标题建议 | 对应文档 | 优先级 |
|---------------|---------|--------|
| `[M1-A] 知识底座：高中物理知识树首版` | MAT-PHY-001 | P0 |
| `[M1-B] StudentTwinAgent 核心字段与状态模型` | TWIN-001/002/003 | P0 |
| `[M1-C] 学习事件生成标准最小集` | INGEST-007 | P0 |
| `[M1-D] 图谱记忆层 MVP` | GRAPH-001 | P1 |
| `[M1-E] 前台观察层 MVP（家长端）` | OBS-001 | P1 |
| `[M1-Gate] 最小闭环交叉验证与收口` | 阶段门控 | P0 |

---

### 阶段二：观察层增强期（Phase 2: Observation Layer Enhancement）

| 属性 | 值 |
|------|------|
| **Linear Milestone name** | `M2 - 观察层增强期` |
| **对应 AEdu 架构层** | 08 观察层与产品层（全量） + 03 教材标准表 + 04 教材与学科库（扩展） |
| **核心目标** | 从家长端 MVP 扩展到老师端 + 学校端，实现三角色观察框架完整覆盖 |
| **验证标准** | 3 角色 × 3 视图（家长/老师/学校），覆盖 ≥3 个学科，支持 ≥3 种数据源 |

**关键交付物**：
- 教材标准表完整版（STD-001/002）
- 教材与学科库扩展至 ≥3 学科（MAT 扩展）
- 老师端观察视图（OBS-002）
- 学校端观察视图（OBS-003）
- 数据接入扩展至 ≥3 种源（INGEST 扩展）

**对应 Linear Issues 建议**：
| Issue 标题建议 | 对应文档 | 优先级 |
|---------------|---------|--------|
| `[M2-A] 教材标准表完整规范` | STD-001/002 | P0 |
| `[M2-B] 学科库扩展至 3 学科` | MAT 扩展 | P0 |
| `[M2-C] 老师端观察视图` | OBS-002 | P0 |
| `[M2-D] 学校端观察视图` | OBS-003 | P1 |
| `[M2-E] 多数据源接入扩展` | INGEST 扩展 | P1 |
| `[M2-F] 多角色观察框架联调` | OBS 综合 | P0 |
| `[M2-Gate] 观察层增强交叉验证与收口` | 阶段门控 | P0 |

---

### 阶段三：推演层建设期（Phase 3: Simulation Layer Construction）

| 属性 | 值 |
|------|------|
| **Linear Milestone name** | `M3 - 推演层建设期` |
| **对应 AEdu 架构层** | 09 推演与决策层 + 10 规则与外部数据 + 07 记忆与图谱引擎（全量） |
| **核心目标** | 建立干预推演、风险预测、志愿填报三大推演能力 |
| **验证标准** | 基于 ≥1 学期历史数据，输出可操作的干预建议，推演结果准确率 ≥70% |

**关键交付物**：
- 干预推演引擎（SIM-001 子集）
- 风险预测模型（SIM-002）
- 规则引擎与地区规则库（RULE-001）
- 图谱记忆层全量（GRAPH-001/002/003 全量）
- 时序记忆与上下文装配（GRAPH-004/005/006）

**对应 Linear Issues 建议**：
| Issue 标题建议 | 对应文档 | 优先级 |
|---------------|---------|--------|
| `[M3-A] 干预推演引擎 MVP` | SIM-001 | P0 |
| `[M3-B] 风险预测模型` | SIM-002 | P1 |
| `[M3-C] 规则引擎与地区规则库` | RULE-001 | P0 |
| `[M3-D] 图谱记忆层全量建设` | GRAPH-001/002/003 | P0 |
| `[M3-E] 时序记忆与上下文装配` | GRAPH-004/005/006 | P1 |
| `[M3-Gate] 推演层交叉验证与收口` | 阶段门控 | P0 |

---

### 阶段四：平台化扩展期（Phase 4: Platform Expansion）

| 属性 | 值 |
|------|------|
| **Linear Milestone name** | `M4 - 平台化扩展期` |
| **对应 AEdu 架构层** | 11 系统架构与工程实现 + 12 实施与试点运营 + 全量产品层 |
| **核心目标** | 完成试点部署、多租户架构、运维体系，准备正式商业化 |
| **验证标准** | ≥3 所试点学校上线运行，系统可用性 ≥99.5%，数据延迟 <5 分钟 |

**关键交付物**：
- 系统架构与部署方案（ARCH-001 全量）
- 多租户与权限体系（ARCH-002）
- 运维监控与告警（ARCH-003）
- 试点运营 SOP（OPS-001）
- 学校接入流程（OPS-002）
- 反馈闭环机制（OPS-003）

**对应 Linear Issues 建议**：
| Issue 标题建议 | 对应文档 | 优先级 |
|---------------|---------|--------|
| `[M4-A] 系统架构与部署方案全量` | ARCH-001 | P0 |
| `[M4-B] 多租户与权限体系` | ARCH-002 | P0 |
| `[M4-C] 运维监控与告警` | ARCH-003 | P1 |
| `[M4-D] 试点运营 SOP` | OPS-001 | P0 |
| `[M4-E] 学校接入流程` | OPS-002 | P0 |
| `[M4-F] 反馈闭环机制` | OPS-003 | P1 |
| `[M4-Gate] 平台化交叉验证与收口` | 阶段门控 | P0 |

---

## 三、Linear API Mutation 字段分析

### 3.1 `milestoneCreate` / `milestoneUpdate` 所需字段

Linear GraphQL API 中 Milestone 对象的核心字段如下：

| 字段名 | 类型 | 必填 | 说明 | 本方案中的值 |
|--------|------|------|------|-------------|
| `teamId` | String | ✅ | 所属团队 ID | 需预先获取 AEdu 团队的 `id` |
| `name` | String | ✅ | Milestone 名称 | `M1 - 最小闭环验证期` 等 |
| `description` | String | ❌ | Milestone 描述 | 各阶段核心目标描述（见上表） |
| `status` | Enum | ❌ | 状态 | 见下方 3.2 节 |
| `targetDate` | ISO8601 Date | ❌ | 目标完成日期 | 需由 PM 确定 |
| `startDate` | ISO8601 Date | ❌ | 目标开始日期 | 需由 PM 确定 |
| `sortOrder` | Float | ❌ | 排序权重 | 见下方 3.3 节 |
| `autoArchive` | Boolean | ❌ | 是否自动归档 | `false` |
| `autoArchiveTime` | Float | ❌ | 自动归档延迟（秒） | 不设 |
| `completedDate` | ISO8601 Date | ❌ | 实际完成日期 | 初始为空 |

### 3.2 Milestone `status` 可选项

Linear API 中 `MilestoneStatus` 枚举值：

| 枚举值 | 含义 | 适用阶段 |
|--------|------|---------|
| `Backlog` | 待排期 | 所有未启动阶段 |
| `Planned` | 已规划 | 当前阶段之前的下一阶段 |
| `Started` | 进行中 | 当前正在执行的阶段 |
| `Completed` | 已完成 | 已通过阶段门控的阶段 |
| `Canceled` | 已取消 | 被废弃的阶段（极少使用） |

**四阶段状态推进建议**：

| 阶段 | 初始状态 | 执行时状态 | 完成后状态 |
|------|---------|-----------|-----------|
| M1 | `Started` | `Started` | `Completed` |
| M2 | `Planned` | `Started` | `Completed` |
| M3 | `Backlog` | `Planned` → `Started` | `Completed` |
| M4 | `Backlog` | `Planned` → `Started` | `Completed` |

### 3.3 Milestone `sortOrder` 建议值

`sortOrder` 是 Linear 内部用于排序的浮点值，数值越小排在越前面。

建议设置：

| Milestone | sortOrder | 说明 |
|-----------|-----------|------|
| M1 - 最小闭环验证期 | `100` | 最先执行，排最前 |
| M2 - 观察层增强期 | `200` | 第二执行 |
| M3 - 推演层建设期 | `300` | 第三执行 |
| M4 - 平台化扩展期 | `400` | 最后执行 |

> **注意**：`sortOrder` 的具体数值没有严格意义，只需保证相对大小正确。
> Linear 内部使用 `100` 作为默认间隔，此处遵循该约定。

### 3.4 `targetDate` 策略建议

`targetDate` 需要由项目负责人根据实际情况设定。建议的时间跨度参考：

| Milestone | 建议持续时间 | targetDate 计算 |
|-----------|-------------|----------------|
| M1 | 4-6 周 | startDate + 4~6 周 |
| M2 | 4-6 周 | M1.targetDate + 4~6 周 |
| M3 | 6-8 周 | M2.targetDate + 6~8 周 |
| M4 | 6-8 周 | M3.targetDate + 6~8 周 |

---

## 四、幂等创建策略

### 4.1 问题

多次执行创建脚本可能导致重复 Milestone。需要保证：
1. 同名 Milestone 在同一 Team 下只存在一个
2. 重复执行时更新已存在的 Milestone，而非创建新的
3. 各阶段 Issues 不重复关联

### 4.2 策略：Upsert by Name

```
流程：
1. 查询 team.milestones，按 name 精确匹配
2. 如果存在 → 调用 milestoneUpdate 更新字段
3. 如果不存在 → 调用 milestoneCreate 创建
```

### 4.3 幂等 Key 设计

| 幂等 Key 组成 | 说明 |
|--------------|------|
| `teamId + name` | 核心幂等键，确保同一团队下同名 Milestone 唯一 |
| `teamId + issueTitle` | Issue 级别幂等，确保同名 Issue 不重复创建 |

### 4.4 幂等执行伪代码

```python
def upsert_milestone(team_id: str, name: str, props: dict) -> Milestone:
    """
    幂等创建/更新 Milestone
    
    幂等保证：
    - 同一 team_id + name 只存在一个 Milestone
    - 已存在时更新，不存在时创建
    """
    existing = query_milestone_by_name(team_id, name)
    
    if existing:
        # 更新已存在的 Milestone
        return linear.milestone_update(
            id=existing.id,
            **{k: v for k, v in props.items() if v is not None}
        )
    else:
        # 创建新的 Milestone
        return linear.milestone_create(
            team_id=team_id,
            name=name,
            **{k: v for k, v in props.items() if v is not None}
        )
```

### 4.5 Issues 关联的幂等策略

```python
def associate_issue_to_milestone(issue_id: str, milestone_id: str):
    """
    幂等关联 Issue 到 Milestone
    
    幂等保证：
    - 已关联的 Issue 不会重复关联
    - 使用 milestoneId 字段设置，Linear API 自动去重
    """
    existing = query_issue(issue_id)
    if existing.milestone_id != milestone_id:
        linear.issue_update(
            id=issue_id,
            milestone_id=milestone_id
        )
```

### 4.6 创建顺序与依赖

为确保幂等创建时依赖关系正确，建议按以下顺序执行：

```
Step 1: 创建/更新所有 4 个 Milestones (M1~M4)
Step 2: 创建/更新各阶段 Issues
Step 3: 将 Issues 关联到对应 Milestone
Step 4: 设置 Issues 之间的依赖关系（Blocking / Blocked by）
```

---

## 五、阶段间依赖关系

### 5.1 Milestone 依赖链

```
M1 (最小闭环验证期)
  │
  ├─→ 必须完成 M1 Gate 后才能进入 M2
  │
M2 (观察层增强期)
  │
  ├─→ 必须完成 M2 Gate 后才能进入 M3
  │
M3 (推演层建设期)
  │
  ├─→ 必须完成 M3 Gate 后才能进入 M4
  │
M4 (平台化扩展期)
```

### 5.2 Issue 级别 Blocking 关系建议

| Blocking Issue | Blocked Issue | 说明 |
|---------------|---------------|------|
| M1-A 知识底座 | M1-B StudentTwinAgent | 知识底座是学生孪生的前置依赖 |
| M1-B StudentTwinAgent | M1-D 图谱记忆层 | 学生模型是图谱记忆的前置依赖 |
| M1-C 事件标准 | M1-D 图谱记忆层 | 事件标准是数据接入的前置依赖 |
| M1-D 图谱记忆层 | M1-E 观察层 MVP | 图谱是观察输出的前置依赖 |
| M1-Gate 收口 | M2 所有 Issues | M1 未通过 Gate，M2 不得启动 |
| M2-Gate 收口 | M3 所有 Issues | 同上 |
| M3-Gate 收口 | M4 所有 Issues | 同上 |

---

## 六、风险分析

### 6.1 高风险项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **Linear API 限流** | 批量创建/更新可能触发 rate limit | 单次操作间加 100ms 延迟，批量操作使用 batching |
| **团队 ID 配置错误** | Milestone 创建到错误的团队 | 创建前通过 `teams` query 验证 teamId 和 name |
| **targetDate 设置不合理** | 阶段目标日期过于激进或保守 | targetDate 应由 PM 根据实际资源情况确定，不由脚本硬编码 |
| **Milestone 名称冲突** | 与已有 Milestone 名称重复 | 使用 `upsert by name` 策略，名称带阶段编号前缀 `M1/M2/M3/M4` |

### 6.2 中风险项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **Issues 描述过长** | Linear API 对 description 有长度限制 | 描述控制在 5000 字符以内，详细内容放入 Issue comments |
| **阶段 Gate 标准不明确** | 阶段完成标准主观化 | 每个 Gate Issue 明确 PASS/BLOCKED 判定标准 |
| **跨阶段依赖断裂** | M2 Issues 依赖 M1 Issues，但 M1 未完全完成 | 使用 Linear 的 `blocking` / `blocked by` 关系显式标注 |
| **sortOrder 冲突** | 手动调整 sortOrder 后与脚本不一致 | 脚本执行时先查询当前 sortOrder，仅在不存在时设置默认值 |

### 6.3 低风险项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **描述 Markdown 格式不兼容** | Linear 支持 Markdown 但有差异 | 创建前在 Linear UI 手动验证格式渲染 |
| **Auto-archive 误删** | autoArchive=true 可能自动归档未完成 Milestone | 所有 Milestone 设置 autoArchive=false |

### 6.4 约束确认

| 约束 | 状态 |
|------|------|
| 本方案不对 Linear 进行实际写入 | ✅ 遵守 |
| 四阶段与 AEdu 架构分层一致 | ✅ 已对齐 CLAUDE-001 |
| 幂等策略覆盖创建和更新 | ✅ 已设计 |
| 阶段间依赖链完整 | ✅ 已定义 |

---

## 七、执行 Checklist（供主代理执行时参考）

在实际执行 Linear Milestone 创建时，建议按以下顺序进行：

- [ ] 1. 获取 AEdu 团队的 `teamId`
- [ ] 2. 验证团队名称，防止误操作
- [ ] 3. 查询现有 Milestones，确认无名称冲突
- [ ] 4. 确定各阶段的 `startDate` 和 `targetDate`
- [ ] 5. 创建 M1~M4 Milestones（使用 upsert 策略）
- [ ] 6. 创建各阶段 Issues
- [ ] 7. 关联 Issues 到对应 Milestone
- [ ] 8. 设置 Issues 之间的 blocking/blocked by 关系
- [ ] 9. 验证所有 Milestone 和 Issues 在 Linear UI 中正确显示
- [ ] 10. 记录创建的 Milestone IDs 和 Issue IDs，供后续追踪

---

## 八、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-001 本方案 | CLAUDE-001 项目记忆文件 | 四阶段定义对齐 CLAUDE-001 中的项目方法论 |
| OPS-LINEAR-001 本方案 | NAV-010 编号与引用规范 | 本文档编号遵循 NAV 规范 |
| OPS-LINEAR-001 本方案 | STR-008 项目阶段目标与里程碑 | 本文档为 STR-008 的 Linear 落地方案 |
| OPS-LINEAR-001 本方案 | github-standard-project-bootstrap.md | 参考了现有 GitHub Projects 管理标准 |

---

**文档状态**：草稿中
**审批人**：待定
**下次评审日期**：待定
