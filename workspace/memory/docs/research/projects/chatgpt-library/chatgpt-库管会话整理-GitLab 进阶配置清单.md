# 库管 (Knowledge Base Manager) - GitLab 进阶配置清单

> 来源：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
> 对话标题：库管
> 整理时间：2026-03-23
> 整理工具：chrome-devtools MCP

---

## 一、分支保护与 MR 规则清单

### 1.1 分支保护总原则

**3 条硬规则**：

1. **main 只能通过 MR 合并**
   - 任何人、任何 bot，都不允许直接 push main

2. **DevBot 是唯一代码写入者**
   - PMBot、QABot、DocBot 都不直接改代码

3. **CI 未通过，不允许合并**
   - 至少要通过当前第一阶段最小 CI：
     - `py_compile`
     - `pytest`

---

### 1.2 main 分支保护规则

| 配置项 | 建议值 | 说明 |
|--------|--------|------|
| Allowed to merge | Maintainer | 只有 Maintainer 可以合并 MR |
| Allowed to push | No one | 没有人可以直接 push main |
| Force push | 禁止 | 不允许强制推送 |
| 删除保护分支 | 禁止 | 不允许删除 main 分支 |
| Code owner approval | 当前阶段可不開 | 先靠角色与 MR 流程控制 |

**合并前检查（建议开启）**：
- [x] 需要 pipeline 成功
- [x] 阻止有冲突的 MR 合并

---

### 1.3 分支命名规则

#### 功能开发分支

```
feat/f1-chapter-tree
feat/f2-knowledge-ingest
feat/f3-ability-map
feat/f4-anchor-link
feat/f5-sample-pack
```

#### 修复类分支

```
fix/twin-contract
fix/pytest-path
fix/anchor-validation
```

#### 杂项维护分支

```
chore/docs-sync
chore/ci-config
```

---

### 1.4 MR 规则清单

#### MR 标题规范

```
<类型>(<范围>): <简短描述>

示例：
feat(F1): 添加章节树节点 schema
fix(F2): 修复知识点准入校验逻辑
chore(CI): 更新 .gitlab-ci.yml 配置
```

#### MR 描述模板

```markdown
## 关联 Issue
- Closes #<issue-number>

## 变更说明
<!-- 描述本次 MR 的主要变更 -->

## 测试验证
- [ ] py_compile 通过
- [ ] pytest 通过
- [ ] 手动验证通过

## 影响范围
<!-- 列出受影响的模块/功能 -->
```

#### MR 合并流程

```
1. DevBot 创建 MR → 状态：Open
2. CI Pipeline 自动运行 → 状态：Running → Passed/Failed
3. QABot 审查并标记 → 状态：Ready to merge
4. PMBot (Maintainer) 合并 → 状态：Merged
```

---

## 二、权限矩阵

### 2.1 GitLab 角色与 Bot 映射

| 角色 | Bot | 建卡 | 改代码 | 合并 MR | 写 Wiki | 触发流水线 |
|------|-----|------|--------|---------|---------|------------|
| **Owner** | 用户 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Maintainer** | PMBot | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Developer** | DevBot | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Developer** | QABot | ❌ | ✅(测试) | ❌ | ❌ | ✅ |
| **Reporter** | DocBot | ❌ | ❌ | ❌ | ✅ | ❌ |

### 2.2 权限说明

**Owner（用户）**：
- 最高权限
- 管理所有设置
- 管理成员权限

**Maintainer（PMBot）**：
- 创建 Issue / 管理看板
- 合并 MR
- 管理 Milestone
- 触发流水线
- 编辑 Wiki

**Developer（DevBot/QABot）**：
- 创建分支
- 提交代码
- 创建 MR
- 触发流水线
- 查看 CI 结果

**Reporter（DocBot）**：
- 查看 Issue
- 编辑 Wiki
- 查看流水线结果

---

## 三、Issue / MR / Wiki 模板文件

### 3.1 目录结构

```
.gitlab/
├── issue_templates/
│   ├── 功能父卡.md
│   ├── 开发子任务.md
│   └── 验收任务.md
└── merge_request_templates/
    └── default.md
```

---

### 3.2 功能父卡模板

**.gitlab/issue_templates/功能父卡.md**：
```markdown
## 目标
<!-- 描述该功能的核心目标 -->

## 范围
<!-- 说明功能覆盖范围和不覆盖的内容 -->

## 交付物
<!-- 列出预期交付物 -->

## 子任务
<!-- 列出关联的子任务 -->
- [ ] T1
- [ ] T2
- [ ] T3

## 完成定义
<!-- 说明功能完成的判断标准 -->
- [ ]
- [ ]
- [ ]

---
**所属阶段**：Phase-1-MVP
**固定执行口径**：安徽 / 高中 / 高一 / 物理 / PHY_PEP_G1_V1
```

---

### 3.3 开发子任务模板

**.gitlab/issue_templates/开发子任务.md**：
```markdown
## 目标
<!-- 描述该任务的目标 -->

## 输入
<!-- 列出任务的输入材料/依赖 -->

## 输出
<!-- 说明任务的交付物 -->

## 前置依赖
<!-- 说明依赖的前置任务 -->

## 验收标准
<!-- 列出验收的具体标准 -->
- [ ]
- [ ]
- [ ]

---
**所属阶段**：Phase-1-MVP
**标签**：phase-1, task, devbot, ready
```

---

### 3.4 验收任务模板

**.gitlab/issue_templates/验收任务.md**：
```markdown
## 验收目标
<!-- 描述验收的核心目标 -->

## 验收依据
<!-- 列出验收的标准和参考文档 -->

## 验收步骤
<!-- 详细说明验收步骤 -->
1.
2.
3.

## 验收结果
<!-- 验收完成后填写 -->
- [ ] 通过
- [ ] 不通过（说明原因：）

## 阻塞点
<!-- 如有阻塞，详细列出 -->

---
**所属阶段**：Phase-1-MVP
**标签**：phase-1, task, qabot, qa
```

---

### 3.5 MR 默认模板

**.gitlab/merge_request_templates/default.md**：
```markdown
## 关联 Issue
- Closes #

## 变更说明
<!-- 描述本次 MR 的主要变更内容 -->

## 测试验证
- [ ] `python -m py_compile` 通过
- [ ] `pytest` 通过
- [ ] 手动验证通过

## 影响范围
<!-- 列出受影响的模块/功能 -->

## 截图/日志（如适用）
<!-- 如有 UI 变更或需要特殊说明，添加截图或日志 -->

## 检查清单
- [ ] 代码符合项目规范
- [ ] 已添加必要的测试
- [ ] 文档已同步更新（如适用）
```

---

## 四、第一阶段完成定义总表

### 4.1 各功能完成定义

| 功能 | 完成定义 |
|------|----------|
| **F1 章节树标准化** | 能表达章/节/小节三级结构；非固定口径数据会被拦截；至少一个章节完整录入并通过校验 |
| **F2 知识点标准入库** | 每个知识点可唯一标识；每个知识点都能挂到合法章节；首批知识点通过准入校验 |
| **F3 能力点映射** | 能力点结构稳定；首批知识点都至少映射一个能力点；映射关系无悬空节点 |
| **F4 锚点/证据挂接** | 锚点可表达教材页码/章节位置/定义/公式/例题/实验等；首批知识点或能力点都有至少一个证据锚点；关系无悬空引用 |
| **F5 最小闭环校验与样例包** | 能跑通"章节树 → 知识点 → 能力点 → 锚点"；能输出通过/失败结论；能指出当前缺口或阻塞点 |

---

### 4.2 Phase-1 总完成定义

**第一阶段 MVP 完成的判断标准**：

1. **代码层面**
   - [ ] 章节树 schema 已实现并通过测试
   - [ ] 知识点 schema 已实现并通过测试
   - [ ] 能力点 schema 已实现并通过测试
   - [ ] 锚点 schema 已实现并通过测试
   - [ ] 闭环校验脚本可执行

2. **数据层面**
   - [ ] 首版章节树样例数据已录入（至少 1 个完整章节）
   - [ ] 首批知识点样例已入库（至少 5-10 个）
   - [ ] 首批能力点样例与映射数据已完成
   - [ ] 首批锚点样例数据已完成

3. **工程层面**
   - [ ] CI Pipeline 可正常运行
   - [ ] 所有测试通过（pytest）
   - [ ] 分支保护规则已配置
   - [ ] MR 流程可正常运作

4. **文档层面**
   - [ ] 所有 Issue 已关闭
   - [ ] MR 已合并
   - [ ] Wiki 文档已同步
   - [ ] 最小验收报告已输出

---

## 五、GitLab Runner 注册与执行规范清单

### 5.1 Runner 角色定位

**硬规则**：
> 本地 Runner 只服务 DevBot 的受控任务，不能变成任意任务的公共执行器。

**Runner 配置原则**：
- Runner 放在本地执行服务器
- Runner 使用 shell executor
- Runner 只接带指定 tag 的 job
- Runner 不接未打标签的 job
- Runner 不承担生产部署

---

### 5.2 Runner 注册前置条件

**网络访问**：
- [ ] GitLab Web 可访问
- [ ] GitLab API 可访问
- [ ] Git SSH 可访问

**本地环境**：
- [ ] Git 已安装
- [ ] Python 3 已安装
- [ ] `python3 -m venv` 可用
- [ ] pytest 可安装

**账号与权限**：
- [ ] DevBot 运行账户已准备
- [ ] 项目代码目录已准备
- [ ] GitLab Runner 注册 token 已准备
- [ ] Git 凭证 / SSH key 已配置

---

### 5.3 Runner 注册命令

```bash
# 安装 GitLab Runner (Ubuntu/Debian)
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt install gitlab-runner

# 注册 Runner
sudo gitlab-runner register

# 按提示输入：
# - GitLab URL: https://gitlab.example.com/
# - Registration token: <从 GitLab 项目设置中获取>
# - Runner description: local-devbot-runner
# - Tags: devbot,shell,local (逗号分隔，不加空格)
# - Executor: shell
```

---

### 5.4 Runner 配置建议

**config.toml 示例**：
```toml
concurrent = 2
check_interval = 0

[[runners]]
  name = "local-devbot-runner"
  url = "https://gitlab.example.com/"
  token = "<runner-token>"
  executor = "shell"
  shell = "bash"
  [runners.custom_build_dir]
  enabled = true
  [runners.cache]
    Type = "local"
    Path = ""
    Shared = true
```

**标签配置**：
- `devbot` - DevBot 专属任务
- `shell` - shell executor
- `local` - 本地执行
- `phase-1` - 第一阶段任务

---

### 5.5 Runner 执行规范

**允许执行的任务**：
- 带 `devbot` 标签的 CI job
- 带 `phase-1` 标签的 CI job
- 与 F1-F5 功能相关的流水线

**禁止执行的任务**：
- 未打标签的 job
- 生产部署任务
- 其他项目的任务

---

## 六、备份与恢复 SOP

### 6.1 GitLab 备份配置

**定时备份任务**：
```bash
# /etc/cron.d/gitlab-backup
0 2 * * * root /usr/bin/gitlab-rake gitlab:backup:create CRON=1
```

**备份保留策略**：
- 每日备份：保留 7 天
- 每周备份：保留 4 周
- 每月备份：保留 3 个月

---

### 6.2 备份恢复流程

```bash
# 1. 停止相关服务
sudo gitlab-ctl stop puma
sudo gitlab-ctl stop sidekiq

# 2. 确认备份文件
ls -la /var/opt/gitlab/backups/

# 3. 恢复备份
sudo gitlab-rake gitlab:backup:restore BACKUP=<timestamp>

# 4. 重新启动服务
sudo gitlab-ctl restart
```

---

## 七、快速参考卡片

### 7.1 Bot 职责速查

| Bot | 职责 | GitLab 操作 |
|-----|------|------------|
| **PMBot** | 任务编排 | 建卡、标签、Milestone、合并 MR |
| **DevBot** | 开发执行 | 提交代码、创建 MR、跑 CI |
| **QABot** | 验收 | 审查 MR、跑测试、标记验收 |
| **DocBot** | 文档 | 更新 Wiki、同步结论 |

---

### 7.2 标签速查

| 标签 | 说明 |
|------|------|
| `phase-1` | 第一阶段 |
| `F1` ~ `F5` | 功能块 |
| `pmbot` / `devbot` / `qabot` / `docbot` | 负责角色 |
| `ready` / `in-progress` / `qa` / `blocked` / `done` | 状态 |
| `P0` / `P1` / `P2` | 优先级 |

---

### 7.3 分支速查

| 分支类型 | 命名格式 | 说明 |
|----------|----------|------|
| 主分支 | `main` | 保护分支，只能通过 MR 合并 |
| 功能分支 | `feat/<功能>` | 功能开发 |
| 修复分支 | `fix/<问题>` | Bug 修复 |
| 杂项分支 | `chore/<内容>` | 文档/配置等 |

---

**维护人**：项目负责人
**版本**：V1.0
**最后更新**：2026-03-23
