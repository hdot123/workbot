# 库管 (Knowledge Base Manager) - GitLab CE 部署方案

> 来源：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
> 对话标题：库管
> 整理时间：2026-03-23
> 整理工具：chrome-devtools MCP

---

## 一、部署方案选择

### 1.1 两套方案对比

| 方案 | 服务器数量 | 适用阶段 | 说明 |
|------|-----------|----------|------|
| **最小可运行方案** | 2 台 | 第一阶段试运行 | 先把流程跑起来 |
| **稳态方案** | 3 台 | 持续使用/生产环境 | 应用与数据库分离，维护简单 |

**建议**：如果你们现在马上要上，先上 2 台。等第一阶段跑顺，再升到 3 台。

---

## 二、最小可运行方案（2 台服务器）

### 2.1 服务器角色划分

#### 服务器 A：云端 GitLab CE 服务器

**职责**：协作与控制平面
- 仓库托管
- Issue / Board / Milestone
- MR 审核
- CI 入口
- 验收记录
- 文档沉淀
- 状态流转
- PMBot/QABot/DocBot 的协作承载面

**放置服务**：
- GitLab CE（Omnibus 一体部署）
- PostgreSQL（随 GitLab）
- Redis（随 GitLab）
- Sidekiq（随 GitLab）
- Gitaly（随 GitLab）
- Nginx / GitLab 内置 Web 服务
- PMBot / QABot / DocBot 的接入脚本或服务

---

#### 服务器 B：本地执行服务器

**职责**：唯一写入执行端
- DevBot 唯一写入执行
- 本地工作区
- Python/测试环境
- 本地代码修改、测试、提交 MR
- GitLab Runner（Shell Runner）

**放置服务**：
- 本地 Git 工作区
- DevBot 运行环境
- Python/pytest/项目运行环境
- 本地 SSH key / Git 凭证
- 本地 IDE / Codex 执行环境
- （可选）GitLab Runner（shell runner，仅本地执行）

---

### 2.2 2 台方案部署清单

#### 服务器 A：云端 GitLab CE 部署

**必须部署**：
- GitLab CE
- PostgreSQL（先随 GitLab Omnibus 一体化）
- Redis（随 GitLab）
- Sidekiq（随 GitLab）
- Gitaly（随 GitLab）
- Nginx / GitLab 内置 Web

**建议配置**：
- CPU：4 核
- 内存：8GB
- 硬盘：100GB SSD
- 操作系统：Ubuntu 22.04 LTS

**部署命令**：
```bash
# 安装 GitLab CE
sudo apt update
sudo apt install -y curl openssh-server postfix git
curl https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
sudo EXTERNAL_URL="http://your-domain.com" apt install gitlab-ce

# 验证服务
sudo gitlab-ctl status
```

---

#### 服务器 B：本地执行环境部署

**必须部署**：
- Git
- Python 3.9+
- pytest
- GitLab Runner（可选）

**建议配置**：
- CPU：4 核
- 内存：8GB
- 硬盘：50GB SSD
- 操作系统：Ubuntu 22.04 LTS / macOS

**部署命令**：
```bash
# 安装 Git 和 Python
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv

# 安装 GitLab Runner（可选）
curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
sudo apt install gitlab-runner

# 配置项目虚拟环境
python3 -m venv /opt/aedu_env
source /opt/aedu_env/bin/activate
pip install pydantic pytest
```

---

## 三、稳态方案（3 台服务器）

### 3.1 服务器角色划分

| 服务器 | 职责 | 放置服务 |
|--------|------|----------|
| **服务器 1**：本地执行服务器 | DevBot 唯一写入端 | DevBot、本地工作区、GitLab Runner |
| **服务器 2**：云端应用服务器 | GitLab 应用层 | GitLab CE Web、Sidekiq、Redis、Gitaly、Nginx |
| **服务器 3**：云端数据服务器 | 数据持久化 | PostgreSQL、备份服务、日志归档 |

---

### 3.2 稳态方案优势

- GitLab 应用和数据库分离，维护简单
- 后面任务量、MR、CI 增多时不容易互相拖垮
- 备份、恢复、迁移更清楚
- 后续接更多 bot 或流水线时，不用重做部署

---

## 四、GitLab CE 初始化配置清单

### 4.1 实例级初始化

#### 基础访问配置

- [ ] 配置 GitLab 域名
- [ ] 开启 HTTPS
- [ ] 开启 SSH clone
- [ ] 配置管理员账号
- [ ] 管理员开启二次验证
- [ ] 配置系统邮件发信

**完成标志**：
- Web 可访问
- SSH 可 clone/push
- 邮件通知可正常发出

---

#### 基础安全配置

- [ ] 关闭匿名访问
- [ ] 关闭公开注册
- [ ] 限制只允许管理员创建顶级 group
- [ ] 启用分支保护策略
- [ ] 配置定时备份

**完成标志**：
- 非授权用户不能注册/访问
- 备份任务可执行

---

### 4.2 Group 初始化

**建议创建顶级 Group**：`AEdu`

**Group 建议配置**：

| 配置项 | 值 |
|--------|-----|
| Group 名称 | AEdu |
| Group URL | `aedu` |
| 可见性 | Private |
| 权限设置 | 只允许 Maintainer 创建项目 |

---

### 4.3 项目初始化

**建议创建项目**：`workbot`

**项目建议配置**：

| 配置项 | 值 |
|--------|-----|
| 项目名称 | workbot |
| 项目 URL | `workbot` |
| 可见性 | Private |
| 默认分支 | `main` |
| 保护分支 | `main`（仅 Maintainer 可推送） |

---

## 五、GitLab 标签清单

### 5.1 阶段标签

| 标签 | 说明 |
|------|------|
| `phase-1` | 第一阶段 MVP（当前使用） |
| `phase-2` | 第二阶段 |
| `phase-3` | 第三阶段 |

---

### 5.2 功能标签

| 标签 | 说明 |
|------|------|
| `F1-chapter-tree` | 章节树标准化 |
| `F2-knowledge-ingest` | 知识点标准入库 |
| `F3-ability-map` | 能力点映射 |
| `F4-anchor-link` | 锚点/证据挂接 |
| `F5-sample-pack` | 最小闭环校验与样例包 |

---

### 5.3 角色标签

| 标签 | 说明 |
|------|------|
| `pmbot` | PMBot 负责任务编排 |
| `devbot` | DevBot 负责开发执行 |
| `qabot` | QABot 负责验收 |
| `docbot` | DocBot 负责文档同步 |

---

### 5.4 状态标签

| 标签 | 说明 |
|------|------|
| `ready` | 就绪可开始 |
| `in-progress` | 进行中 |
| `qa` | 待验收 |
| `blocked` | 阻塞 |
| `done` | 已完成 |

---

### 5.5 优先级标签（可选）

| 标签 | 说明 |
|------|------|
| `P0` | 最高优先级 |
| `P1` | 高优先级 |
| `P2` | 正常优先级 |

---

### 5.6 类型标签（可选）

| 标签 | 说明 |
|------|------|
| `feature` | 功能卡 |
| `task` | 任务卡 |
| `bug` | 缺陷修复 |
| `documentation` | 文档相关 |

---

## 六、Board 看板列配置

### 6.1 看板列结构

```
待办 (Open) → 就绪 (ready) → 进行中 (in-progress) → 待验收 (qa) → 已完成 (done)
                                    ↓
                                阻塞 (blocked)
```

### 6.2 列与标签映射

| 看板列 | 对应标签 | 说明 |
|--------|----------|------|
| 待办 | 无标签 | 新创建的 Issue |
| 就绪 | `ready` | 已准备好可以开始的任务 |
| 进行中 | `in-progress` | 已开始开发的任务 |
| 待验收 | `qa` | 开发完成等待验收 |
| 阻塞 | `blocked` | 遇到阻塞无法继续 |
| 已完成 | `done` | 验收通过的任务 |

---

## 七、Milestone 配置

### 7.1 Phase-1-MVP

| 配置项 | 值 |
|--------|-----|
| 名称 | Phase-1-MVP |
| 描述 | 第一阶段最小可运行产品：跑通"章节树 → 知识点 → 能力点 → 锚点 → 校验结果"闭环 |
| 开始日期 | 2026-03-23 |
| 截止日期 | （根据实际情况设定） |
| 关联 Issue | 5 个功能父卡 + 15 个子任务卡 |

---

## 八、Bot 与 GitLab 映射

### 8.1 Bot 职责映射

| Bot | GitLab 操作 |
|-----|------------|
| **PMBot** | 创建 Issue、设置标签、管理 Milestone、调整优先级 |
| **DevBot** | 提交代码、创建 MR、更新 Issue 状态为 `qa` |
| **QABot** | 审查 MR、运行 CI、更新 Issue 状态为 `done` 或 `blocked` |
| **DocBot** | 更新 Wiki、同步 Issue 结论到文档 |

---

### 8.2 不要按 bot 数量配服务器

**重要原则**：
- bot 是角色，不是服务
- 多个 bot 可以跑在同一台服务器上
- 服务器分配应按职责分离，而非 bot 数量

**正确做法**：
- DevBot 独立在本地执行服务器
- PMBot/QABot/DocBot 可以都在云端 GitLab CE 服务器上

---

## 九、部署检查清单

### 9.1 部署前检查

- [ ] 确定服务器数量和配置
- [ ] 准备域名和 SSL 证书
- [ ] 准备管理员账号邮箱
- [ ] 确认网络连接和防火墙规则

### 9.2 部署后验证

- [ ] GitLab Web 可正常访问
- [ ] SSH clone/push 可正常工作
- [ ] 邮件通知可正常发送
- [ ] 备份任务可正常执行
- [ ] Runner 可正常注册和执行

---

**维护人**：项目负责人
**版本**：V1.0
**最后更新**：2026-03-23
