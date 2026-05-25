# Workbot 记忆系统全景文档

> 文档层级：`workspace/memory/docs/`
> 性质：总览与导航文档，不是 canonical
> 当前 canonical 以 `workspace/memory/kb/global/` 与 `workspace/memory/kb/projects/` 为准
> 更新：2026-04-11

---

## 1. 总览

`workbot` 只有一套总记忆系统。

这套系统的本体位于 `/Users/busiji/workbot/workspace`，由以下层级组成：

1. `workspace/INDEX.md` 与 `workspace/NOW.md`：Boot / State
2. `workspace/project-map/`：Legality Map / Ingestion Registry
3. `workspace/memory/log/`：Fact Log
4. `workspace/memory/kb/`：Canonical Knowledge Base
5. `workspace/memory/docs/`：Reference Corpus
6. `workspace/projects/` 与 `workspace/artifacts/`：Execution / Delivery

`AEdu` 不是第二套并列记忆系统，而是这套总记忆系统中的一个项目域。

如果需要查看正式定义，请以以下 canonical 为准：

- `/Users/busiji/workbot/workspace/project-map/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-system.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-routing.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-hook-contract.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-project-map-governance.md`
- `/Users/busiji/workbot/workspace/memory/kb/projects/INDEX.md`

---

## 2. 总系统层级

### 2.1 Boot / State

入口文件：

- `/Users/busiji/workbot/workspace/INDEX.md`
- `/Users/busiji/workbot/workspace/NOW.md`

职责：

- 定义加载顺序
- 定义硬规则
- 提供当前状态面板

边界：

- `INDEX.md` 负责入口与边界，不负责长期真相
- `NOW.md` 负责短期状态，是唯一常规覆写的状态文件

### 2.2 Legality Map / Ingestion Registry

目录：

- `/Users/busiji/workbot/workspace/project-map/`

职责：

- 声明谁是当前唯一合法系统
- 将未清洗资料降级为待吞噬原料或兼容残留
- 为 hook / gateway 提供登录前 gate

边界：

- 地图中的登记不等于已经吸收完成
- 但未登记内容不得被继续视为合法资料

### 2.3 Fact Log

目录：

- `/Users/busiji/workbot/workspace/memory/log/`

职责：

- 记录发生过什么
- 保留时间线和现场事实

边界：

- append-only
- 不是长期真相层

### 2.4 Canonical Knowledge Base

目录：

- `/Users/busiji/workbot/workspace/memory/kb/global/`
- `/Users/busiji/workbot/workspace/memory/kb/projects/`
- `/Users/busiji/workbot/workspace/memory/kb/decisions/`
- `/Users/busiji/workbot/workspace/memory/kb/lessons/`

职责：

- `global/`：跨项目稳定规则
- `projects/`：项目域 stable facts 与派生规则
- `decisions/`：正式裁决
- `lessons/`：经验教训

边界：

- 只有 `kb/` 承担长期真相职责
- `docs/`、`projects/`、`artifacts/` 都不能越级替代它

### 2.5 Reference Corpus

目录：

- `/Users/busiji/workbot/workspace/memory/docs/`

职责：

- 放来源材料、研究资料、草稿、对比稿和说明文档

边界：

- `docs/` 不是 canonical
- 资料如果上升为稳定规则，必须提炼回 `kb/`

### 2.6 Execution / Delivery

目录：

- `/Users/busiji/workbot/workspace/projects/`
- `/Users/busiji/workbot/workspace/artifacts/`

职责：

- 项目执行清单
- 交接材料
- 导出结果
- 截图和运行产物

边界：

- 这里是执行面与产物层，不定义长期真相

---

## 3. 项目域关系

### 3.1 `workbot`

`workbot` 是仓库级控制面与项目容器，本身承载这套总记忆系统。

项目 canonical：

- `/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md`

### 3.2 `AEdu`

`AEdu` 是总记忆系统中的业务项目域。

它的项目规范来自总记忆系统的派生，不是第二套总系统。

项目 canonical：

- `/Users/busiji/workbot/workspace/memory/kb/projects/AEdu.md`

项目执行入口：

- `/Users/busiji/workbot/workspace/projects/AEdu/INDEX.md`

研究资料入口：

- `/Users/busiji/workbot/workspace/memory/docs/research/projects/AEdu/INDEX.md`

### 3.3 `platform-capabilities`

共享能力域统一归口于：

- `/Users/busiji/workbot/workspace/memory/kb/projects/platform-capabilities.md`

它描述 `app/`、`agents/`、`gpt-web-to/` 等共享能力域与项目容器之间的稳定关系。

---

## 4. 路由原则

当前总记忆系统的写入边界由以下 canonical 定义：

- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-routing.md`

核心分流原则如下：

- 事实写 `memory/log/`
- 跨项目规则写 `memory/kb/global/`
- 项目稳定规则写 `memory/kb/projects/`
- 裁决写 `memory/kb/decisions/`
- 教训写 `memory/kb/lessons/`
- 来源资料写 `memory/docs/`
- 执行材料写 `workspace/projects/`
- 导出产物写 `workspace/artifacts/`
- 系统错误写 `workspace/memory/system/errors.log`
- 被证伪或失效的记忆证据写 `workspace/memory/archive/invalid/`

这条分流明确区分了：

- `docs` 与 `kb`
- `projects` 与 `artifacts`
- `error` 与 `invalid`

---

## 5. 宿主与 Hook 的位置

`Codex`、`Claude`、`cmux`、检索实现、sqlite 派生层、hook gateway 都属于支持层，不属于总记忆系统本体。

这意味着：

- 宿主可以影响上下文注入方式
- 宿主不能重写总记忆系统规则
- hook 是进入总记忆系统的统一入口合同，不是新的真相层

正式 hook 合同见：

- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-hook-contract.md`

当前执行策略：

- 总项目地图目录已建立，用于声明唯一合法系统与待吞噬原料区
- 总记忆系统结构与 canonical 已先完成收正
- `Codex` 与 `Claude` 的正式 hook 入口现已统一接到 `workspace/tools/memory_hook_gateway.py`
- gateway 会先生成 context package 与验收证据，再委托到底层 `cmux` hook

---

## 6. 上游借鉴源的地位

`passkills/OpenClaw` 可以作为上游借鉴源，但不能直接等同为本仓 canonical。

可借鉴的内容包括：

- 分层思想
- canonical / docs / log / archive 的边界
- 宿主与真相层分离的思路

不能直接照搬的内容包括：

- 宿主专属 bootstrap 语义
- OpenClaw 专属 sqlite / hook / runtime 假设
- 把项目特例误写成总系统本体的说法

因此，本仓采用的是：

- 本地 canonical 优先
- 上游材料作为来源与参考
- 任何借来的规则都要先经本地裁决，才能进入 `kb/`

---

## 7. 当前正确口径

如果只保留一句话，当前正确口径是：

**`workbot` 只有一套总记忆系统；`AEdu` 是其中的项目域；`docs` 是资料层，`kb` 是真相层，`projects/artifacts` 是执行层，宿主与 hook 是支持层。**

---

## 8. 相关阅读

- `/Users/busiji/workbot/workspace/INDEX.md`
- `/Users/busiji/workbot/workspace/NOW.md`
- `/Users/busiji/workbot/workspace/memory/kb/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/kb/projects/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/docs/INDEX.md`
