# GitHub Project CLI 运行规范（workbot）

## 1. 目的

本文件是 `workbot` 仓库内长期复用的 GitHub Project 操作规范。

目标：

1. 固化 GitHub Project 的标准创建与维护流程。
2. 禁止每次临时重新摸索 GitHub Project 的操作方式。
3. 明确何时必须新建 Project，何时只允许往现有 Project 加 item。
4. 固化阶段 item 的最小结构，保证所有阶段任务都可验收。

本文件关注 **GitHub Project 的操作规范**，不替代项目管理分层说明。

相关文档：

- [`github-standard-project-bootstrap.md`](/Users/busiji/workbot/docs/project-management/github-standard-project-bootstrap.md)
- [`github-projects-product-analysis-2026-04-16.md`](/Users/busiji/workbot/docs/project-management/github-projects-product-analysis-2026-04-16.md)

## 2. 硬约束

### 2.1 GitHub 操作面

GitHub 相关操作只允许以下路径：

- `gh`
- `gh api`
- GitHub GraphQL API

明确禁止：

- 浏览器 UI
- 手工网页点击
- 依赖浏览器完成 GitHub Project 创建、改字段、补视图

### 2.2 Project 视图要求

正式 GitHub Project 默认必须同时具备以下三种视图：

1. `Table`
2. `Board`
3. `Roadmap`

仅有 `Table` 的临时 Project 不算正式交付面。

### 2.3 阶段 item 要求

每个正式阶段 item 必须同时包含：

1. `Goal`
2. `Subtasks`
3. `Acceptance Checklist`

不允许只有标题，没有子任务和验收条件。

### 2.4 GitHub Project 作为验收面

当某项工作需要：

- 独立阶段管理
- 独立 roadmap
- 独立阶段验收
- 独立责任 bot / 状态流转

则必须新建 Project，而不是把内容塞进旧 Project 或单个 issue 评论流。

## 3. 当前标准创建路径

### 3.1 不推荐路径

直接执行：

```bash
gh project create --owner <owner> --title "<title>"
```

问题：

- 该命令默认只得到一个 `Table` 视图。
- CLI 当前没有公开的 “create view” 命令来补 `Board / Roadmap`。

因此，这条路径只适合做临时探测，不适合作为正式创建方式。

### 3.2 正式路径

正式创建新 Project 时，必须优先复制一个已经验证过的三视图模板 Project：

```bash
gh project copy <template_number> \
  --source-owner <owner> \
  --target-owner <owner> \
  --title "<new_project_title>"
```

然后再编辑标题、描述、readme、字段和 item。

### 3.3 视图验证

复制后必须立即验证新 Project 是否具备三视图：

```bash
gh api graphql -f query='
query {
  user(login:"<owner>") {
    projectV2(number:<project_number>) {
      title
      views(first:20) {
        nodes {
          name
          layout
          number
        }
      }
    }
  }
}'
```

通过标准：

- 存在 `TABLE_LAYOUT`
- 存在 `BOARD_LAYOUT`
- 存在 `ROADMAP_LAYOUT`

## 4. 模板 Project 规则

### 4.1 模板选择原则

可作为模板的 Project 必须满足：

1. 已验证存在 `Table / Board / Roadmap`
2. 字段集合可复用
3. 状态流与 bot 字段不与当前任务冲突

### 4.2 当前已验证模板

截至 `2026-04-18`，在 `hdot123` 下已验证可复制的三视图模板包括：

1. `Project #5` `workbot-mainline-standard-board`
2. `Project #8` `workbot cmux Phase 0-4 Execution Plan`

其中：

- `Project #5` 视图和字段更完整，更适合作为标准模板
- `Project #8` 适合轻量 phase 型项目，但字段更少

### 4.3 模板复制后的清理规则

如果因为探测先创建了一个只有 `Table` 的临时 Project：

1. 先完成模板复制，得到正式 Project
2. 确认正式 Project 三视图齐全
3. 删除临时单视图 Project

不允许账号下长期保留同名临时脏 Project。

## 5. 何时必须新建 Project

以下情况必须新建 Project：

1. 新工作包需要独立的验收面
2. 新工作包需要独立 roadmap
3. 新工作包和现有 Project 的阶段/字段体系明显不同
4. 新工作包是一个完整交付物，而不是已有交付物下的子阶段
5. 用户明确要求 “必须新建 Project”

## 6. 何时只加 item

以下情况只允许加 item，不应新建 Project：

1. 任务仍属于现有交付物的同一验收面
2. 任务只是现有 roadmap 下的新增阶段或补丁阶段
3. 任务字段、状态流、bot 归属与现有 Project 兼容
4. 任务只是某个阶段内部拆分，而不是新项目

## 7. 正式 Project 的最小字段集

复制模板后，至少应保留或补齐以下字段：

| 字段 | 类型 | 用途 |
|---|---|---|
| `Status` | Single select | 看板状态流转 |
| `Priority` | Single select | 优先级 |
| `Execution Bot` | Single select | 当前执行 bot |
| `Gate Bot` | Single select | 验收 bot |
| `Track` | Single select | 主线/治理/硬化等轨道 |
| `Formal Dispatch` | Single select | 是否正式派发 |
| `Source` | Text | 任务来源 |
| `Scope Guard` | Text | 范围边界 |
| `Start Date` | Date | roadmap 起始时间 |
| `Target Date` | Date | roadmap 目标时间 |

如果 `Roadmap` 需要真正可用，必须补 `Start Date` / `Target Date` 两个 Date 字段。

创建示例：

```bash
gh project field-create <project_number> \
  --owner <owner> \
  --name "Start Date" \
  --data-type DATE

gh project field-create <project_number> \
  --owner <owner> \
  --name "Target Date" \
  --data-type DATE
```

## 8. 阶段 item 模板

每个阶段 draft item 的正文至少使用以下结构：

```md
## Goal
一句话说明本阶段的结果目标。

## Subtasks
- [ ] 子任务 1
- [ ] 子任务 2
- [ ] 子任务 3

## Acceptance Checklist
- [ ] 验收项 1
- [ ] 验收项 2
- [ ] 验收项 3
```

### 8.1 Subtasks 书写规则

子任务必须：

- 可执行
- 可分派
- 可被完成/未完成判断

不允许：

- 空泛口号
- “继续推进”
- “完善一下”
- 没有对象和动作的描述

### 8.2 Acceptance Checklist 书写规则

验收项必须：

- 能判断通过/失败
- 尽量与具体证据绑定
- 尽量避免纯主观描述

建议优先写成：

- 是否存在某类文档/报告
- 是否达到某个覆盖率或完整性
- 是否能够本地跑通某条链路
- 是否生成某类验证证据

## 9. 推荐创建顺序

正式创建新 Project 时，遵循以下顺序：

1. 选定三视图模板 Project
2. 执行 `gh project copy`
3. 用 GraphQL 验证三视图
4. 编辑标题、description、readme
5. 补齐 `Start Date / Target Date` 等缺失字段
6. 创建阶段 draft items
7. 为每个阶段 item 回填字段
8. 列出 items 做最终核验
9. 删除误建的临时单视图 Project

## 10. 标准命令清单

### 10.1 列出 Project

```bash
gh project list --owner <owner>
```

### 10.2 复制模板 Project

```bash
gh project copy <template_number> \
  --source-owner <owner> \
  --target-owner <owner> \
  --title "<new_title>"
```

### 10.3 编辑 Project 基本信息

```bash
gh project edit <project_number> \
  --owner <owner> \
  --title "<title>" \
  --description "<description>" \
  --readme "<markdown>"
```

### 10.4 列字段

```bash
gh project field-list <project_number> --owner <owner> --format json
```

### 10.5 创建 draft item

```bash
gh project item-create <project_number> \
  --owner <owner> \
  --title "<phase_title>" \
  --body "<markdown_body>"
```

### 10.6 回填 item 字段

```bash
gh project item-edit \
  --id <project_item_id> \
  --project-id <project_id> \
  --field-id <field_id> \
  --single-select-option-id <option_id>
```

Date/Text 字段分别用：

```bash
--date YYYY-MM-DD
--text "..."
```

### 10.7 列 items 做核验

```bash
gh project item-list <project_number> --owner <owner> --format json
```

### 10.8 删除误建 Project

```bash
printf 'y\n' | gh project delete <project_number> --owner <owner>
```

## 11. Project 建成后的最低核验标准

一个新 Project 建完后，至少要同时满足：

1. 三视图齐全
2. description/readme 已写
3. 阶段 items 已建
4. 每个阶段 item 都有 `Subtasks + Acceptance Checklist`
5. 核心字段已回填
6. 如果使用 roadmap，已有 `Start Date / Target Date`

否则不算正式交付。

## 12. 反模式

以下做法在 `workbot` 中视为反模式：

1. 每次都重新研究怎么操作 GitHub Project
2. 用浏览器点击 GitHub Project
3. 直接 `gh project create` 后把单视图 project 当正式项目交付
4. 只建标题，不写阶段子任务和验收条件
5. 不回填字段，导致 Board / Roadmap 没有可用信息
6. 临时 project 不清理，污染账号项目列表

## 13. 维护规则

当 GitHub CLI / API 行为发生变化时，应更新本文件，而不是继续把新的经验散落在聊天记录中。

如果出现新的三视图模板 Project，也应在本文件中补充已验证模板列表。
