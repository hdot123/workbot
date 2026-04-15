# GitHub 项目管理初始化清单

本仓库采用以下三层职责：

- GitHub Projects = 整体项目计划盘 / 总览层
- Milestones = 某个版本 / 阶段目标
- Issues = 单个正式任务

## 1. Labels 初始化
建议创建以下 labels：

### type
- type:feature
- type:bug
- type:refactor
- type:docs
- type:ops
- type:test

### area
- area:frontend
- area:backend
- area:infra
- area:data
- area:docs
- area:test

### prio
- prio:p0
- prio:p1
- prio:p2
- prio:p3

### status
- status:blocked
- status:needs-spec
- status:needs-test
- status:duplicate
- status:wontfix
- status:question

## 2. Milestones 初始化
建议按阶段式创建：
- M1 - 行为锁定
- M2 - 接口与依赖反转
- M3 - 策略注入
- M4 - core 仓内抽离
- M5 - adapter 收薄与迁移验证
- M6 - 独立仓库可行性评估
- M-H - 稳定性增强

## 3. Project 初始化
建议 Project 名称：
- Memory Modularization Master Board

### 建议字段
- Status
- Priority
- Area
- Size
- Risk
- Owner
- Start date
- Target date
- Iteration

### Status 值
- Backlog
- Ready
- In Progress
- In Review
- Blocked
- Done

### Priority 值
- P0
- P1
- P2
- P3

### Area 值
- frontend
- backend
- infra
- data
- docs
- test

### Size 值
- XS
- S
- M
- L
- XL

### Risk 值
- low
- medium
- high

### 建议视图
- Master Table
- Execution Board
- Roadmap
- Current Iteration
- By Milestone

## 4. 当前模块化任务映射建议

### 主线 Milestones
- Round 1 / 当前已完成内容 -> M1 - 行为锁定
- Round 2 正式任务设计与实施 -> M2 - 接口与依赖反转
- policy-pack 注入 -> M3 - 策略注入
- memory-core 仓内抽离 -> M4 - core 仓内抽离
- adapter 收薄与迁移验证 -> M5 - adapter 收薄与迁移验证
- 独立仓库可行性评估 -> M6 - 独立仓库可行性评估

### 并线 Milestone
- hardening_backlog -> M-H - 稳定性增强

## 5. Round 1 Issues 建议
- [Task] Round 1 Package A - 基础行为面锁定
- [Task] Round 1 Package B - 路由与状态面锁定
- [Task] Round 1 Package C - 日志与产物面锁定
- [Task] Round 1 Package D - Delegate 边界与 parity 基线锁定
- [Task] Round 1 final gate

## 6. 下一步推荐
1. 在 GitHub UI 中创建 labels
2. 在 GitHub UI 中创建 milestones
3. 在 GitHub UI 中创建项目总盘与字段/视图
4. 将现有与后续模块化任务统一转为 issues 并挂入 Project + Milestone
5. 以 Project 作为后续唯一总览层
