# 项目管理规则

## 任务分层
- Issue = 单个任务
- Milestone = 阶段/版本目标
- Project = 整体项目总盘

## 状态流转
Backlog -> Ready -> In Progress -> In Review -> Done
卡住时进入 Blocked

## 必填项
每个 Issue 必须有：
- type
- priority
- area
- milestone
- 验收标准

## 拆分规则
满足以下任一条件必须拆分：
- 预计超过 1 周
- 涉及多个模块
- 无法写清晰验收标准
- 包含多个独立结果

## 收口规则
- Milestone 到期时，只做完成/迁移，不悬挂
- Done 必须以“已合并/已验证/已交付”为标准
- Blocked 必须写明阻塞原因

## GitHub Projects 标准字段
- Status
- Priority
- Area
- Size
- Risk
- Owner
- Start date
- Target date
- Iteration

## GitHub Projects 标准视图
- Master Table
- Execution Board
- Roadmap

## 状态定义
- Backlog：已记录，未准备开工
- Ready：需求清楚，可以做
- In Progress：正在开发/处理中
- In Review：PR、验证、评审中
- Blocked：被依赖、环境、决策卡住
- Done：合并、验收、关闭
