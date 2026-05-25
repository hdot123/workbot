# GitHub 标准项目管理引导（workbot）

## 1. 当前正式承载标准

- **GitHub Projects** = 整体项目计划盘 / 总览层
- **Milestones** = 某个版本 / 阶段目标
- **Issues** = 单个正式任务

这三层职责固定，不再使用单个 Issue 评论流承载完整总盘。

## 2. Issue #4 的固定职责

`Issue #4: main-thread-task-board` 只保留以下职责：

1. 治理规则
2. 临时任务源切换
3. 必要的主线程结果汇总口径

以下内容**不得再继续堆入 Issue #4 评论流**：

- 完整模块化总计划
- 阶段总盘
- 轮次总览
- 长期进度表
- Round 全量工作包总盘

## 3. 推荐 Project 设定

### Project 名称

`workbot-mainline-standard-board`

### 推荐视图

1. **Board**：按状态流转查看
2. **Table**：按字段批量维护
3. **Roadmap**：按 Milestone 查看阶段推进

### 推荐字段

| 字段 | 类型 | 说明 |
|---|---|---|
| Status | Single select | `Todo` / `In Progress` / `In Review` / `Gate` / `Blocked` / `Done` |
| Track | Single select | `Mainline` / `Hardening` / `PR-Hygiene` / `Governance` |
| Priority | Single select | `P0` / `P1` / `P2` |
| Execution Bot | Single select | `pm-bot` / `dev-bot` / `qa-bot` / `doc-bot` / `rea-bot` |
| Gate Bot | Single select | `qa-bot` / `rea-bot` / `qa+rea` / `none` |
| Formal Dispatch | Single select | `Yes` / `No` |
| Source | Text | 例如：`Issue #4` |
| Scope Guard | Text | 例如：`Round 1 only / no Round 2 leakage` |
| Blocked By | Text | 阻塞项 |

## 4. 推荐 Milestones

建议按模块化主线建立以下 Milestones：

- `M0 - PM Setup`
- `M1 - Round 1 Characterization`
- `M2 - Round 2 Interface Seams`
- `M3 - Round 3 Policy Pack Injection`
- `M4 - Round 4 In-Repo Memory Core Extraction`
- `M5 - Round 5 Adapter Slimming`
- `M6 - Round 6 Standalone Repo Evaluation`

### 说明

- `hardening_backlog` 不并入 M1~M6 主线里程碑，应作为 **Track = Hardening** 单独管理。
- `pr2_post_main_recheck_ready_and_merge` 不并入模块化主线，应作为 **Track = PR-Hygiene** 管理。

## 5. 推荐 Labels

建议至少建立：

- `mainline`
- `hardening`
- `pr-hygiene`
- `governance`
- `round1`
- `round2`
- `round3`
- `round4`
- `round5`
- `round6`
- `gate`
- `blocked`

## 6. Round 1 首批正式 Issues

在 Project 建立后，建议首先创建以下正式任务：

1. `[Round1-A] Core behavior characterization`
2. `[Round1-B] Routing and state characterization`
3. `[Round1-C] Logging and artifact characterization`
4. `[Round1-D] Delegate boundary and parity baseline`
5. `[Round1-Gate] Cross-validation and closeout`

上述 5 个 Issue 应统一：

- 加入 Project：`workbot-mainline-standard-board`
- Milestone：`M1 - Round 1 Characterization`
- Track：`Mainline`
- Formal Dispatch：`Yes`

## 7. 创建顺序（标准落地顺序）

1. 建立 GitHub Project 作为总盘
2. 建立 Milestones 作为阶段包
3. 建立 Labels 作为筛选维度
4. 创建单个正式任务 Issues
5. 将 Issues 加入 Project 并补齐字段
6. 以后仅通过 Project 总盘推进主线，不再把总盘继续堆入 Issue #4 评论流

## 8. 当前主线的判定规则

- **Projects**：看全局处于哪一轮、下一步是什么
- **Milestones**：看某一轮是否完成、是否可进入下一轮
- **Issues**：看单个正式任务由谁执行、范围是什么、是否 blocked

## 9. 当前推荐下一步

按当前标准口径，下一步不是继续扩写 Issue #4 评论，而是：

1. 建立 `workbot-mainline-standard-board`
2. 建立 `M0 ~ M6` Milestones
3. 创建 Round 1 的 4 个 package issues 和 1 个 gate issue
4. 将 `hardening_backlog` 与 `PR-Hygiene` 从模块化主线中明确分轨
