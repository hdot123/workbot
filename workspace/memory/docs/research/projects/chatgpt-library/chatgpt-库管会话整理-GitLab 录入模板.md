# 库管 (Knowledge Base Manager) - GitLab Issue 批量录入模板

> 来源：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
> 对话标题：库管
> 整理时间：2026-03-23
> 整理工具：chrome-devtools MCP

---

## 一、批量录入字段模板

**统一前提**：
- **Milestone**：Phase-1-MVP
- **固定执行口径**：安徽 / 高中 / 高一 / 物理 / PHY_PEP_G1_V1

**建议统一字段**：

| 字段 | 说明 |
|------|------|
| `title` | Issue 标题 |
| `description` | Issue 正文 |
| `labels` | 逗号分隔 |
| `milestone` | 统一 Phase-1-MVP |
| `issue_type` | 建议自定义为 feature 或 task |
| `parent` | 子任务挂到哪个父卡下（如 GitLab 不支持父子字段，在正文里写"所属父卡：F1/F2/..."） |

---

## 二、TSV 数据模板

```tsv
title	milestone	labels	issue_type	parent	description
[F1] 章节树标准化	Phase-1-MVP	phase-1,feature,F1-chapter-tree,pmbot,P0,ready	feature		目标：完成 PHY_PEP_G1_V1 高中物理必修一首个章节的标准化章节树建模，形成可挂载、可校验、可引用的章节骨架。范围：仅覆盖首个章节，至少到章/节/小节三级。完成定义：能表达章/节/小节三级结构；非固定口径数据会被拦截；至少一个章节完整录入并通过校验。
[F2] 知识点标准入库	Phase-1-MVP	phase-1,feature,F2-knowledge-ingest,pmbot,P0,ready	feature		目标：建立知识点最小入库模型，并为首个章节产出第一批可入库知识点。范围：仅覆盖首个章节，不做全册铺开。完成定义：每个知识点可唯一标识；每个知识点都能挂到合法章节；首批知识点通过准入校验。
[F3] 能力点映射	Phase-1-MVP	phase-1,feature,F3-ability-map,pmbot,P1,ready	feature		目标：建立能力点最小模型，并完成首批知识点到能力点的映射。范围：仅覆盖首个章节，不扩展完整能力体系。完成定义：能力点结构稳定；首批知识点都至少映射一个能力点；映射关系无悬空节点。
[F4] 锚点/证据挂接	Phase-1-MVP	phase-1,feature,F4-anchor-link,pmbot,P1,ready	feature		目标：建立锚点最小模型，并为首批知识点/能力点挂接教材证据。范围：仅覆盖首个章节的首批样例。完成定义：首批知识点或能力点都有至少一个证据锚点；关系无悬空引用。
[F5] 最小闭环校验与样例包	Phase-1-MVP	phase-1,feature,F5-sample-pack,pmbot,P1,ready	feature		目标：把前 4 个功能串起来，形成第一份完整样例包，为后续批量复制提供模板。范围：仅覆盖首个章节。完成定义：能完整展示章节树→知识点→能力点→锚点→校验结果全链路；能明确回答"是否跑通"；可直接作为第一阶段演示样例。
[F1-T1] 定义章节树节点模型	Phase-1-MVP	phase-1,task,F1-chapter-tree,devbot,ready	task	F1	目标：建立章节树最小对象模型，支持章/节/小节三级。输入：STR-002、KB-001、MAT-PHY-001、当前固定执行口径。输出：章节树 schema。核心字段：node_id、node_type、name、parent_id、subject、grade、edition、version、scope、status。验收标准：能表达章/节/小节三级、编码唯一、父子关系可校验、与固定口径字段兼容。
[F1-T2] 实现固定口径校验	Phase-1-MVP	phase-1,task,F1-chapter-tree,devbot,ready	task	F1	目标：把当前冻结口径变成硬校验规则。输入：当前冻结口径（安徽/高中/高一/物理/PHY_PEP_G1_V1）。输出：口径校验规则/校验函数。前置依赖：F1-T1。验收标准：非安徽/高中/高一/物理/PHY_PEP_G1_V1 数据被拒绝、错误信息可定位字段、可被后续知识点/能力点/锚点复用。
[F1-T3] 录入首版章节树样例	Phase-1-MVP	phase-1,task,F1-chapter-tree,devbot,ready	task	F1	目标：完成必修一首个章节的章节树样例。输入：必修一章节目录、F1-T1 schema、F1-T2 口径校验。输出：首版章节树样例数据（至少包含 1 个完整章节的章/节/小节结构）。前置依赖：F1-T1、F1-T2。验收标准：至少包含章、节、小节三级、所有节点通过口径校验、父子关系完整、编码无冲突。
[F2-T1] 定义知识点对象模型	Phase-1-MVP	phase-1,task,F2-knowledge-ingest,devbot,ready	task	F2	目标：建立知识点最小入库模型。输入：KB-001、KB-004、MAT-PHY-001、F1 输出。输出：知识点 schema。核心字段：knowledge_id、name、chapter_node_id、definition、aliases、status、source_ref。验收标准：知识点可独立存储、必填字段完整、状态枚举清晰、与章节树节点可关联。
[F2-T2] 定义知识点准入规则	Phase-1-MVP	phase-1,task,F2-knowledge-ingest,devbot,ready	task	F2	目标：实现知识点入库校验。输入：F2-T1 schema、F1-T2 口径校验。输出：知识点准入规则/校验函数。前置依赖：F1-T2、F2-T1。验收标准：无章节归属的知识点被拒绝、空定义被拒绝、同名冲突可检测、口径不匹配被拒绝。
[F2-T3] 产出首批知识点样例	Phase-1-MVP	phase-1,task,F2-knowledge-ingest,devbot,ready	task	F2	目标：为首个章节生成第一批知识点条目。输入：首个章节内容、F2-T1 schema、F2-T2 准入规则。输出：首批知识点样例数据（至少 5-10 个知识点）。前置依赖：F1-T3、F2-T1、F2-T2。验收标准：所有知识点通过准入校验、每个知识点挂靠到章节树节点、定义清晰无歧义。
[F3-T1] 定义能力点对象模型	Phase-1-MVP	phase-1,task,F3-ability-map,devbot,ready	task	F3	目标：建立能力点最小模型。输入：STD-002、KB-004。输出：能力点 schema。核心字段：ability_id、name、description、level、category、status。验收标准：能力点可独立存储、能力分级清晰、类别可枚举。
[F3-T2] 定义知识点→能力点映射规则	Phase-1-MVP	phase-1,task,F3-ability-map,devbot,ready	task	F3	目标：建立 knowledge -> ability 关系规则。输入：F2-T3 知识点样例、F3-T1 schema。输出：映射规则/关系 schema。前置依赖：F2-T3、F3-T1。核心规则：一个知识点可映射多个能力点、一个能力点可被多个知识点支撑、必须有主归属。验收标准：映射关系可存储、可查询、可校验。
[F3-T3] 产出首批能力点样例	Phase-1-MVP	phase-1,task,F3-ability-map,devbot,ready	task	F3	目标：给首批知识点挂上能力点。输入：F2-T3 知识点样例、F3-T2 映射规则。输出：首批能力点样例与映射数据。前置依赖：F2-T3、F3-T1、F3-T2。验收标准：每个能力点至少挂靠一个知识点、映射关系完整、能力点类型覆盖理解/辨析/应用/建模/实验解释。
[F4-T1] 定义锚点对象模型	Phase-1-MVP	phase-1,task,F4-anchor-link,devbot,ready	task	F4	目标：建立锚点最小模型。输入：KB-004、STD-002、教材内容。输出：锚点 schema。核心字段：anchor_id、anchor_type、source_ref、page_or_section、excerpt、target_type、target_id。锚点类型：章节位置、教材页码、定义、公式、例题、实验、图示、题型样例。验收标准：锚点类型可枚举、证据片段可存储、目标引用可追溯。
[F4-T2] 定义锚点引用关系	Phase-1-MVP	phase-1,task,F4-anchor-link,devbot,ready	task	F4	目标：建立锚点与知识点/能力点的关系规则。输入：F2-T3、F3-T3、F4-T1。输出：锚点关系 schema / 规则。前置依赖：F2-T3、F3-T3、F4-T1。核心规则：一个锚点可服务多个知识点/能力点、必须有主归属、引用可双向追溯。验收标准：关系可存储、可查询、可校验、支持断链检测。
[F4-T3] 产出首批锚点样例	Phase-1-MVP	phase-1,task,F4-anchor-link,devbot,ready	task	F4	目标：为首批知识点/能力点补证据锚点。输入：F2-T3、F3-T3、F4-T2。输出：首批锚点样例数据。前置依赖：F4-T2。验收标准：每个知识点至少有一个锚点、每个能力点至少有一个锚点、锚点类型覆盖≥3 种、无悬空锚点。
[F5-T1] 定义最小闭环校验规则	Phase-1-MVP	phase-1,task,F5-sample-pack,devbot,ready	task	F5	目标：把前四组对象和关系串成一套整包校验。输入：F1/F2/F3/F4 全部输出。输出：闭环校验规则/校验脚本。前置依赖：F1-T3、F2-T3、F3-T3、F4-T3。校验项：范围合法（冻结口径内）、节点不孤立（所有章节树节点有知识点、所有知识点有能力点、所有能力点有锚点）、关系完整、锚点可追溯。验收标准：校验脚本可执行、能检测出孤立节点、能检测出断链、能输出校验报告。
[F5-T2] 组装首个完整样例包	Phase-1-MVP	phase-1,task,F5-sample-pack,devbot,ready	task	F5	目标：形成第一份可演示、可验收的章节样例包。输入：F1/F2/F3/F4 全部样例。输出：完整样例包。前置依赖：F5-T1。内容至少包括：章节树数据、知识点数据、能力点数据、锚点数据、关系数据、校验结果。验收标准：样例包可完整展示闭环、数据结构一致、可直接作为第一阶段演示样例。
[F5-T3] 输出最小验收结果	Phase-1-MVP	phase-1,task,F5-sample-pack,devbot,ready	task	F5	目标：形成第一阶段的可交付验收结论。输入：F5-T2 完整样例包。输出：最小验收报告。前置依赖：F5-T2。开发动作：核对口径是否一致、核对链路是否跑通、列出缺口和后续建议、输出明确结论。验收标准：能明确回答"是否跑通"、能明确列出阻塞点、可作为阶段收口材料。
```

---

## 三、GitLab API 批量建卡请求模板

### 3.1 功能父卡创建示例（F1）

```bash
curl --request POST \
  --header "PRIVATE-TOKEN: <your_access_token>" \
  --data "title=[F1] 章节树标准化" \
  --data "description=目标：完成 PHY_PEP_G1_V1 高中物理必修一首个章节的标准化章节树建模，形成可挂载、可校验、可引用的章节骨架。

范围：仅覆盖首个章节，至少到章/节/小节三级。

完成定义：
- 能表达章/节/小节三级结构
- 非固定口径数据会被拦截
- 至少一个章节完整录入并通过校验" \
  --data "labels=phase-1,feature,F1-chapter-tree,pmbot,P0,ready" \
  --data "milestone_id=<milestone_id>" \
  "https://gitlab.example.com/api/v4/projects/<project_id>/issues"
```

### 3.2 子任务卡创建示例（F1-T1）

```bash
curl --request POST \
  --header "PRIVATE-TOKEN: <your_access_token>" \
  --data "title=[F1-T1] 定义章节树节点模型" \
  --data "description=**目标**：建立章节树最小对象模型，支持章/节/小节三级

**输入**：STR-002、KB-001、MAT-PHY-001、当前固定执行口径

**输出**：章节树 schema

**核心字段**：
- node_id
- node_type
- name
- parent_id
- subject
- grade
- edition
- version
- scope
- status

**验收标准**：能表达章/节/小节三级、编码唯一、父子关系可校验、与固定口径字段兼容

**所属父卡**：F1" \
  --data "labels=phase-1,task,F1-chapter-tree,devbot,ready" \
  --data "milestone_id=<milestone_id>" \
  --data "epic_id=<F1_epic_id>" \
  "https://gitlab.example.com/api/v4/projects/<project_id>/issues"
```

### 3.3 批量创建脚本框架（Python 示例）

```python
import requests

GITLAB_TOKEN = "<your_access_token>"
PROJECT_ID = "<project_id>"
MILESTONE_ID = "<milestone_id>"

HEADERS = {
    "PRIVATE-TOKEN": GITLAB_TOKEN,
    "Content-Type": "application/x-www-form-urlencoded"
}

# 功能父卡列表
parent_issues = [
    {
        "title": "[F1] 章节树标准化",
        "description": "目标：完成 PHY_PEP_G1_V1 高中物理必修一首个章节的标准化章节树建模...",
        "labels": "phase-1,feature,F1-chapter-tree,pmbot,P0,ready"
    },
    # ... F2, F3, F4, F5
]

# 子任务卡列表
child_issues = [
    {
        "title": "[F1-T1] 定义章节树节点模型",
        "description": "**目标**：建立章节树最小对象模型...",
        "labels": "phase-1,task,F1-chapter-tree,devbot,ready",
        "parent_title": "[F1] 章节树标准化"
    },
    # ... 其他子任务
]

def create_issue(title, description, labels, epic_id=None):
    data = {
        "title": title,
        "description": description,
        "labels": labels,
        "milestone_id": MILESTONE_ID
    }
    if epic_id:
        data["epic_id"] = epic_id

    response = requests.post(
        f"https://gitlab.example.com/api/v4/projects/{PROJECT_ID}/issues",
        headers=HEADERS,
        data=data
    )
    return response.json()

# 先创建功能父卡
epic_ids = {}
for parent in parent_issues:
    result = create_issue(**parent)
    epic_ids[parent["title"]] = result["iid"]
    print(f"Created {parent['title']}: {result['web_url']}")

# 再创建子任务卡
for child in child_issues:
    parent_epic_id = epic_ids.get(child["parent_title"])
    result = create_issue(
        title=child["title"],
        description=child["description"],
        labels=child["labels"],
        epic_id=parent_epic_id
    )
    print(f"Created {child['title']}: {result['web_url']}")
```

---

## 四、标签集合统一约定

| 标签类别 | 标签值 | 说明 |
|---------|--------|------|
| **阶段** | `phase-1` | 第一阶段 MVP |
| **功能** | `F1-chapter-tree` | 章节树标准化 |
| | `F2-knowledge-ingest` | 知识点入库 |
| | `F3-ability-map` | 能力点映射 |
| | `F4-anchor-link` | 锚点挂接 |
| | `F5-sample-pack` | 样例包与校验 |
| **角色** | `pmbot` | 项目负责人（功能父卡） |
| | `devbot` | 开发（子任务卡） |
| | `qabot` | 测试验收 |
| | `docbot` | 文档同步 |
| **优先级** | `P0` | 最高优先级 |
| | `P1` | 高优先级 |
| | `P2` | 正常优先级 |
| **状态** | `ready` | 就绪可开始 |
| | `in-progress` | 进行中 |
| | `qa` | 待验收 |
| | `blocked` | 阻塞 |
| | `done` | 已完成 |
| **类型** | `feature` | 功能卡 |
| | `task` | 任务卡 |
| | `bug` | 缺陷修复 |
| | `documentation` | 文档相关 |

---

## 五、5 个功能父卡 + 15 个子任务卡详情

### 5.1 功能父卡

#### 父卡 F1：章节树标准化

**标题**：`[F1] 章节树标准化`

**正文**：
```
## 目标
完成 PHY_PEP_G1_V1 高中物理必修一首个章节的标准化章节树建模，形成可挂载、可校验、可引用的章节骨架。

## 范围
- 仅覆盖首个章节
- 至少到"章 / 节 / 小节"三级

## 交付物
- 章节树节点 schema
- 固定执行口径校验规则
- 首版章节树样例数据

## 子任务
- F1-T1 定义章节树节点模型
- F1-T2 实现固定口径校验
- F1-T3 录入首版章节树样例

## 完成定义
- 能表达章/节/小节三级结构
- 非固定口径数据会被拦截
- 至少一个章节完整录入并通过校验
```

**标签**：`phase-1, feature, F1-chapter-tree, pmbot, P0, ready`

---

#### 父卡 F2：知识点标准入库

**标题**：`[F2] 知识点标准入库`

**正文**：
```
## 目标
建立知识点最小入库模型，并为首个章节产出第一批可入库知识点。

## 范围
- 仅覆盖首个章节
- 不做全册铺开

## 交付物
- 知识点 schema
- 知识点准入规则
- 首批知识点样例

## 子任务
- F2-T1 定义知识点对象模型
- F2-T2 定义知识点准入规则
- F2-T3 产出首批知识点样例

## 完成定义
- 每个知识点可唯一标识
- 每个知识点都能挂到合法章节
- 首批知识点通过准入校验
```

**标签**：`phase-1, feature, F2-knowledge-ingest, pmbot, P0, ready`

---

#### 父卡 F3：能力点映射

**标题**：`[F3] 能力点映射`

**正文**：
```
## 目标
建立能力点最小模型，并完成首批知识点到能力点的映射。

## 范围
- 仅覆盖首个章节
- 不扩展完整能力体系

## 交付物
- 能力点 schema
- 知识点→能力点映射规则
- 首批能力点与映射样例

## 子任务
- F3-T1 定义能力点对象模型
- F3-T2 定义知识点→能力点映射规则
- F3-T3 产出首批能力点样例

## 完成定义
- 能力点结构稳定
- 首批知识点都至少映射一个能力点
- 映射关系无悬空节点
```

**标签**：`phase-1, feature, F3-ability-map, pmbot, P1, ready`

---

#### 父卡 F4：锚点/证据挂接

**标题**：`[F4] 锚点/证据挂接`

**正文**：
```
## 目标
建立锚点最小模型，并为首批知识点/能力点挂接教材证据。

## 范围
- 仅覆盖首个章节的首批样例

## 交付物
- 锚点 schema
- 锚点引用关系规则
- 首批锚点样例

## 子任务
- F4-T1 定义锚点对象模型
- F4-T2 定义锚点引用关系
- F4-T3 产出首批锚点样例

## 完成定义
- 锚点可表达教材页码/章节位置/定义/公式/例题/实验等
- 首批知识点或能力点都有至少一个证据锚点
- 关系无悬空引用
```

**标签**：`phase-1, feature, F4-anchor-link, pmbot, P1, ready`

---

#### 父卡 F5：最小闭环校验与样例包

**标题**：`[F5] 最小闭环校验与样例包`

**正文**：
```
## 目标
把章节树、知识点、能力点、锚点串成首个完整样例包，并输出最小验收结果。

## 范围
- 仅验证首个章节样例闭环

## 交付物
- 闭环校验规则/脚本
- 完整样例包
- 最小验收报告

## 子任务
- F5-T1 定义最小闭环校验规则
- F5-T2 组装首个完整样例包
- F5-T3 输出最小验收结果

## 完成定义
- 能跑通"章节树 → 知识点 → 能力点 → 锚点"
- 能输出通过/失败结论
- 能指出当前缺口或阻塞点
```

**标签**：`phase-1, feature, F5-sample-pack, pmbot, P1, ready`

---

### 5.2 子任务卡（15 个）

#### F1-T1：定义章节树节点模型

**标题**：`[F1-T1] 定义章节树节点模型`

**正文**：
```
## 目标
建立章节树节点最小 schema。

## 输入
- STR-002
- KB-001
- MAT-PHY-001
- 固定执行口径

## 输出
章节树 schema

## 核心字段
- node_id
- node_type
- name
- parent_id
- subject
- grade
- edition
- region
- status

## 前置依赖
无

## 验收标准
- 能表达章/节/小节三级
- 编码唯一
- 父子关系可校验
```

**标签**：`phase-1, task, F1-chapter-tree, devbot, ready`

---

#### F1-T2：实现固定口径校验

**标题**：`[F1-T2] 实现固定口径校验`

**正文**：
```
## 目标
把当前冻结执行口径固化成校验规则。

## 输入
固定执行口径（安徽/高中/高一/物理/PHY_PEP_G1_V1）

## 输出
口径校验函数/规则

## 前置依赖
F1-T1

## 验收标准
- 非安徽/高中/高一/物理/PHY_PEP_G1_V1 数据被拒绝或标记无效
- 错误信息可定位字段
- 可复用于章节树/知识点/能力点/锚点
```

**标签**：`phase-1, task, F1-chapter-tree, devbot, ready`

---

#### F1-T3：录入首版章节树样例

**标题**：`[F1-T3] 录入首版章节树样例`

**正文**：
```
## 目标
完成必修一首个章节的章节树样例。

## 输入
- 必修一章节目录
- F1-T1 schema
- F1-T2 口径校验

## 输出
首版章节树样例数据（至少包含 1 个完整章节的章/节/小节结构）

## 前置依赖
F1-T1、F1-T2

## 验收标准
- 至少包含章、节、小节三级
- 所有节点通过口径校验
- 父子关系完整
- 编码无冲突
```

**标签**：`phase-1, task, F1-chapter-tree, devbot, ready`

---

#### F2-T1：定义知识点对象模型

**标题**：`[F2-T1] 定义知识点对象模型`

**正文**：
```
## 目标
建立知识点最小入库模型。

## 输入
- KB-001
- KB-004
- MAT-PHY-001
- F1 输出

## 输出
知识点 schema

## 核心字段
- knowledge_id
- name
- chapter_node_id
- definition
- aliases
- status
- source_ref

## 前置依赖
F1 输出

## 验收标准
- 知识点可独立存储
- 必填字段完整
- 状态枚举清晰
- 与章节树节点可关联
```

**标签**：`phase-1, task, F2-knowledge-ingest, devbot, ready`

---

#### F2-T2：定义知识点准入规则

**标题**：`[F2-T2] 定义知识点准入规则`

**正文**：
```
## 目标
实现知识点入库校验。

## 输入
- F2-T1 schema
- F1-T2 口径校验

## 输出
知识点准入规则/校验函数

## 前置依赖
F1-T2、F2-T1

## 验收标准
- 无章节归属的知识点被拒绝
- 空定义被拒绝
- 同名冲突可检测
- 口径不匹配被拒绝
```

**标签**：`phase-1, task, F2-knowledge-ingest, devbot, ready`

---

#### F2-T3：产出首批知识点样例

**标题**：`[F2-T3] 产出首批知识点样例`

**正文**：
```
## 目标
为首个章节生成第一批知识点条目。

## 输入
- 首个章节内容
- F2-T1 schema
- F2-T2 准入规则

## 输出
首批知识点样例数据（至少 5-10 个知识点）

## 前置依赖
F1-T3、F2-T1、F2-T2

## 验收标准
- 所有知识点通过准入校验
- 每个知识点挂靠到章节树节点
- 定义清晰无歧义
```

**标签**：`phase-1, task, F2-knowledge-ingest, devbot, ready`

---

#### F3-T1：定义能力点对象模型

**标题**：`[F3-T1] 定义能力点对象模型`

**正文**：
```
## 目标
建立能力点最小模型。

## 输入
- STD-002
- KB-004

## 输出
能力点 schema

## 核心字段
- ability_id
- name
- description
- level
- category
- status

## 前置依赖
F2 输出

## 验收标准
- 能力点可独立存储
- 能力分级清晰
- 类别可枚举
```

**标签**：`phase-1, task, F3-ability-map, devbot, ready`

---

#### F3-T2：定义知识点→能力点映射规则

**标题**：`[F3-T2] 定义知识点→能力点映射规则`

**正文**：
```
## 目标
建立 knowledge -> ability 关系规则。

## 输入
- F2-T3 知识点样例
- F3-T1 schema

## 输出
映射规则/关系 schema

## 前置依赖
F2-T3、F3-T1

## 核心规则
- 一个知识点可映射多个能力点
- 一个能力点可被多个知识点支撑
- 必须有主归属

## 验收标准
- 映射关系可存储
- 可查询
- 可校验
```

**标签**：`phase-1, task, F3-ability-map, devbot, ready`

---

#### F3-T3：产出首批能力点样例

**标题**：`[F3-T3] 产出首批能力点样例`

**正文**：
```
## 目标
给首批知识点挂上能力点。

## 输入
- F2-T3 知识点样例
- F3-T2 映射规则

## 输出
首批能力点样例与映射数据

## 前置依赖
F2-T3、F3-T1、F3-T2

## 验收标准
- 每个能力点至少挂靠一个知识点
- 映射关系完整
- 能力点类型覆盖理解/辨析/应用/建模/实验解释
```

**标签**：`phase-1, task, F3-ability-map, devbot, ready`

---

#### F4-T1：定义锚点对象模型

**标题**：`[F4-T1] 定义锚点对象模型`

**正文**：
```
## 目标
建立锚点最小模型。

## 输入
- KB-004
- STD-002
- 教材内容

## 输出
锚点 schema

## 核心字段
- anchor_id
- anchor_type
- source_ref
- page_or_section
- excerpt
- target_type
- target_id

## 锚点类型
- 章节位置
- 教材页码
- 定义
- 公式
- 例题
- 实验
- 图示
- 题型样例

## 前置依赖
F2/F3 输出

## 验收标准
- 锚点类型可枚举
- 证据片段可存储
- 目标引用可追溯
```

**标签**：`phase-1, task, F4-anchor-link, devbot, ready`

---

#### F4-T2：定义锚点引用关系

**标题**：`[F4-T2] 定义锚点引用关系`

**正文**：
```
## 目标
建立锚点与知识点/能力点的关系规则。

## 输入
- F2-T3
- F3-T3
- F4-T1

## 输出
锚点关系 schema / 规则

## 前置依赖
F2-T3、F3-T3、F4-T1

## 核心规则
- 一个锚点可服务多个知识点/能力点
- 必须有主归属
- 引用可双向追溯

## 验收标准
- 关系可存储
- 可查询
- 可校验
- 支持断链检测
```

**标签**：`phase-1, task, F4-anchor-link, devbot, ready`

---

#### F4-T3：产出首批锚点样例

**标题**：`[F4-T3] 产出首批锚点样例`

**正文**：
```
## 目标
为首批知识点/能力点补证据锚点。

## 输入
- F2-T3
- F3-T3
- F4-T2

## 输出
首批锚点样例数据

## 前置依赖
F4-T2

## 验收标准
- 每个知识点至少有一个锚点
- 每个能力点至少有一个锚点
- 锚点类型覆盖≥3 种
- 无悬空锚点
```

**标签**：`phase-1, task, F4-anchor-link, devbot, ready`

---

#### F5-T1：定义最小闭环校验规则

**标题**：`[F5-T1] 定义最小闭环校验规则`

**正文**：
```
## 目标
把前四组对象和关系串成一套整包校验。

## 输入
F1/F2/F3/F4 全部输出

## 输出
闭环校验规则/校验脚本

## 前置依赖
F1-T3、F2-T3、F3-T3、F4-T3

## 校验项
- 范围合法（冻结口径内）
- 节点不孤立（所有章节树节点有知识点、所有知识点有能力点、所有能力点有锚点）
- 关系完整
- 锚点可追溯

## 验收标准
- 校验脚本可执行
- 能检测出孤立节点
- 能检测出断链
- 能输出校验报告
```

**标签**：`phase-1, task, F5-sample-pack, devbot, qabot, ready`

---

#### F5-T2：组装首个完整样例包

**标题**：`[F5-T2] 组装首个完整样例包`

**正文**：
```
## 目标
形成第一份可演示、可验收的章节样例包。

## 输入
F1/F2/F3/F4 全部样例

## 输出
完整样例包

## 前置依赖
F5-T1

## 内容至少包括
- 章节树数据
- 知识点数据
- 能力点数据
- 锚点数据
- 关系数据
- 校验结果

## 验收标准
- 样例包可完整展示闭环
- 数据结构一致
- 可直接作为第一阶段演示样例
```

**标签**：`phase-1, task, F5-sample-pack, devbot, ready`

---

#### F5-T3：输出最小验收结果

**标题**：`[F5-T3] 输出最小验收结果`

**正文**：
```
## 目标
形成第一阶段的可交付验收结论。

## 输入
F5-T2 完整样例包

## 输出
最小验收报告

## 前置依赖
F5-T2

## 开发动作
- 核对口径是否一致
- 核对链路是否跑通
- 列出缺口和后续建议
- 输出明确结论

## 验收标准
- 能明确回答"是否跑通"
- 能明确列出阻塞点
- 可作为阶段收口材料
```

**标签**：`phase-1, task, F5-sample-pack, qabot, ready`

---

## 六、5 个功能父卡 + 15 个子任务卡的默认标签分配表

| 任务编号 | 任务名称 | 阶段标签 | 功能标签 | 角色标签 | 优先级 | 状态标签 | 类型标签 |
|----------|----------|----------|----------|----------|--------|----------|----------|
| F1 | 章节树标准化 | phase-1 | F1-chapter-tree | pmbot | P0 | ready | feature |
| F2 | 知识点标准入库 | phase-1 | F2-knowledge-ingest | pmbot | P0 | ready | feature |
| F3 | 能力点映射 | phase-1 | F3-ability-map | pmbot | P1 | ready | feature |
| F4 | 锚点/证据挂接 | phase-1 | F4-anchor-link | pmbot | P1 | ready | feature |
| F5 | 最小闭环校验与样例包 | phase-1 | F5-sample-pack | pmbot | P1 | ready | feature |
| F1-T1 | 定义章节树节点模型 | phase-1 | F1-chapter-tree | devbot | P0 | ready | task |
| F1-T2 | 实现固定口径校验 | phase-1 | F1-chapter-tree | devbot | P0 | ready | task |
| F1-T3 | 录入首版章节树样例 | phase-1 | F1-chapter-tree | devbot | P0 | ready | task |
| F2-T1 | 定义知识点对象模型 | phase-1 | F2-knowledge-ingest | devbot | P0 | ready | task |
| F2-T2 | 定义知识点准入规则 | phase-1 | F2-knowledge-ingest | devbot | P0 | ready | task |
| F2-T3 | 产出首批知识点样例 | phase-1 | F2-knowledge-ingest | devbot | P0 | ready | task |
| F3-T1 | 定义能力点对象模型 | phase-1 | F3-ability-map | devbot | P1 | ready | task |
| F3-T2 | 定义知识点→能力点映射 | phase-1 | F3-ability-map | devbot | P1 | ready | task |
| F3-T3 | 产出首批能力点样例 | phase-1 | F3-ability-map | devbot | P1 | ready | task |
| F4-T1 | 定义锚点对象模型 | phase-1 | F4-anchor-link | devbot | P1 | ready | task |
| F4-T2 | 定义锚点引用关系 | phase-1 | F4-anchor-link | devbot | P1 | ready | task |
| F4-T3 | 产出首批锚点样例 | phase-1 | F4-anchor-link | devbot | P1 | ready | task |
| F5-T1 | 定义最小闭环校验规则 | phase-1 | F5-sample-pack | devbot,qabot | P1 | ready | task |
| F5-T2 | 组装首个完整样例包 | phase-1 | F5-sample-pack | devbot | P1 | ready | task |
| F5-T3 | 输出最小验收结果 | phase-1 | F5-sample-pack | qabot | P1 | ready | task |

---

## 七、GitLab Board 列配置

### 7.1 看板列结构

```
待办 (Open) → 就绪 (ready) → 进行中 (in-progress) → 待验收 (qa) → 已完成 (done)
                                    ↓
                                阻塞 (blocked)
```

### 7.2 列与标签映射

| 看板列 | 对应标签 | 说明 |
|--------|----------|------|
| 待办 | 无标签 | 新创建的 Issue |
| 就绪 | `ready` | 已准备好可以开始的任务 |
| 进行中 | `in-progress` | 已开始开发的任务 |
| 待验收 | `qa` | 开发完成等待验收 |
| 阻塞 | `blocked` | 遇到阻塞无法继续 |
| 已完成 | `done` | 验收通过的任务 |

### 7.3 看板筛选器建议

| 筛选器名称 | 标签组合 | 用途 |
|------------|----------|------|
| 本周任务 | `phase-1, ready` | 查看当前可开始的任务 |
| 开发中 | `phase-1, in-progress, devbot` | 查看 DevBot 正在执行的任务 |
| 待验收 | `phase-1, qa` | 查看等待 QABot 验收的任务 |
| 阻塞任务 | `phase-1, blocked` | 查看需要解决的阻塞 |
| PMBot 视图 | `phase-1, pmbot` | 查看所有功能父卡 |
| DevBot 视图 | `phase-1, devbot` | 查看所有开发子任务 |
| QABot 视图 | `phase-1, qabot` | 查看所有验收任务 |

---

## 八、Milestone 配置文案

### 8.1 Phase-1-MVP

**名称**：`Phase-1-MVP`

**描述**：
```
## 第一阶段最小可运行产品

### 目标
跑通"章节树 → 知识点 → 能力点 → 锚点 → 校验结果"完整闭环。

### 固定执行口径
- 地区：安徽
- 学段：高中
- 年级：高一
- 学科：物理
- 教材版本：PHY_PEP_G1_V1

### 范围限制
- 仅覆盖首个章节
- 不扩展到 OBS/SIM
- 不扩展到大规模 GRAPH 正式建模
- 不铺全册、全学科、全版本

### 包含内容
- 5 个功能父卡
- 15 个子任务卡

### 交付物
1. 章节树 schema + 首版章节树样例数据
2. 知识点 schema + 首批知识点样例数据
3. 能力点 schema + 首批能力点样例与映射数据
4. 锚点 schema + 首批锚点样例数据
5. 闭环校验脚本 + 完整样例包 + 最小验收报告
```

**开始日期**：2026-03-23

**截止日期**：（根据实际情况设定，建议 2-4 周）

---

## 九、.gitlab-ci.yml 增强版

### 9.1 完整版 CI/CD 配置

```yaml
# .gitlab-ci.yml
# AEdu 项目 - 第一阶段 MVP CI/CD 配置

stages:
  - validate      # 代码校验
  - test         # 测试执行
  - build        # 构建打包
  - deploy       # 部署（可选）

# 全局变量
variables:
  PYTHON_VERSION: "3.9"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  PYTHONDONTWRITEBYTECODE: "1"
  PYTHONIOENCODING: "utf-8"

# 缓存配置
cache:
  paths:
    - .cache/pip/
    - .venv/

# 规则配置
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"

# ======================
# 阶段 1: 代码校验
# ======================

# Python 代码语法校验
validate-python:
  stage: validate
  image: python:${PYTHON_VERSION}
  script:
    - python -m py_compile app/models/constants.py
    - python -m py_compile app/models/twin_ingest_contract.py
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - app/models/*.py
    - if: $CI_COMMIT_BRANCH == "main"
      changes:
        - app/models/*.py

# 代码风格检查（可选）
lint-python:
  stage: validate
  image: python:${PYTHON_VERSION}
  script:
    - pip install flake8
    - flake8 app/models/ --max-line-length=100 --ignore=E501,W503
  allow_failure: true
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# ======================
# 阶段 2: 测试执行
# ======================

# 单元测试
unit-tests:
  stage: test
  image: python:${PYTHON_VERSION}
  before_script:
    - python -V
    - pip install -r requirements.txt || pip install pydantic pytest
  script:
    - pytest tests/test_twin_ingest_contract.py -v --tb=short --maxfail=3
  coverage: '/TOTAL.*\s+(\d+%)/'
  artifacts:
    reports:
      junit: junit-report.xml
    when: always
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - app/models/*.py
        - tests/*.py
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"

# 契约测试（TWIN 专属）
contract-tests:
  stage: test
  image: python:${PYTHON_VERSION}
  before_script:
    - pip install pydantic pytest
  script:
    - pytest tests/test_twin_ingest_contract.py::TestTwinIngestContract -v
  rules:
    - if: $CI_PIPELINE_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - app/models/twin_ingest_contract.py
    - if: $CI_COMMIT_BRANCH == "main"

# ======================
# 阶段 3: 构建打包
# ======================

# 构建报告
build-report:
  stage: build
  image: python:${PYTHON_VERSION}
  before_script:
    - pip install pytest pytest-cov
  script:
    - pytest tests/ --cov=app/models --cov-report=html --cov-report=term
  artifacts:
    paths:
      - htmlcov/
      - .coverage
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    expire_in: 1 week
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

# ======================
# 阶段 4: 部署（可选）
# ======================

# 部署到测试环境
deploy-staging:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
  script:
    - echo "Deploying to staging environment..."
    # - ssh deploy@staging "cd /opt/aedu && git pull && ./deploy.sh"
  environment:
    name: staging
    url: https://staging.aedu.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "develop"

# 部署到生产环境
deploy-production:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
  script:
    - echo "Deploying to production environment..."
    # - ssh deploy@production "cd /opt/aedu && git pull && ./deploy.sh"
  environment:
    name: production
    url: https://aedu.example.com
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

---

### 9.2 最小可用版 .gitlab-ci.yml

```yaml
# .gitlab-ci.yml - 最小可用版
# 适用于第一阶段 MVP

stages:
  - validate
  - test

validate:
  stage: validate
  image: python:3.9
  script:
    - python -m py_compile app/models/constants.py
    - python -m py_compile app/models/twin_ingest_contract.py
    - python -m py_compile tests/test_twin_ingest_contract.py

test:
  stage: test
  image: python:3.9
  before_script:
    - pip install pydantic pytest
  script:
    - pytest tests/test_twin_ingest_contract.py -v
```

---

**维护人**：项目负责人
**版本**：V1.1
**最后更新**：2026-03-23
