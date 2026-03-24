# opencli 操作手册

> 版本：V1.0
> 最后更新：2026-03-23
> 维护人：工作空间管理员

---

## 目录

1. [opencli 简介](#一 opencli 简介)
2. [安装与配置](#二安装与配置)
3. [基础命令](#三基础命令)
4. [Skills 使用指南](#四 skills-使用指南)
5. [底层命令详解](#五底层命令详解)
6. [浏览器集成](#六浏览器集成)
7. [故障排查](#七故障排查)

---

## 一、opencli 简介

### 1.1 什么是 opencli

**opencli** 是一个 AI 原生的 CLI 工具框架，核心定位是：

> **把任何网站、Electron 应用、本地工具变成命令行工具**

### 1.2 核心能力

| 能力 | 说明 | 示例 |
|------|------|------|
| **网站 CLI 化** | 通过浏览器自动化，把网站变成命令 | `opencli bilibili hot` |
| **桌面应用 CLI 化** | 控制 Electron 应用 | `opencli chatgpt ask` |
| **外部 CLI 枢纽** | 统一调用现有 CLI 工具 | `opencli gh pr list` |
| **AI 原生** | 自动发现 API、生成适配器 | `opencli explore` |
| **Skills 系统** | AI 可调用的技能定义 | `skill: "gpt-web-to"` |

### 1.3 支持的网站/应用

**社交媒体**：微博、知乎、小红书、B 站、Twitter、Reddit、YouTube...

**桌面应用**：ChatGPT、Cursor、Codex、Notion、Discord、Antigravity...

**工具枢纽**：gh (GitHub CLI)、docker、kubectl、obsidian...

---

## 二、安装与配置

### 2.1 安装方式

#### 方式 1：从 npm 安装（推荐）

```bash
npm install -g @jackwener/opencli
```

#### 方式 2：从本地项目链接（开发用）

```bash
cd /Users/busiji/workbot/opencli
npm link
```

### 2.2 验证安装

```bash
opencli --version
opencli list
```

### 2.3 前置要求

| 要求 | 说明 |
|------|------|
| **Node.js** | >= 20.0.0 |
| **Chrome** | 已安装并登录目标网站 |
| **Browser Bridge 扩展** | Chrome 扩展需安装并启用 |

### 2.4 环境变量配置

```bash
# 通用配置
export OPENCLI_BROWSER_CONNECT_TIMEOUT=60
export OPENCLI_BROWSER_COMMAND_TIMEOUT=60

# AdsPower 指纹浏览器
export ADSPOWER_API_KEY="你的 API Key"
export OPENCLI_BROWSER_BACKEND=adspower
export OPENCLI_BROWSER_PROFILE_ID="你的浏览器 ID"
```

---

## 三、基础命令

### 3.1 命令列表

```bash
# 查看所有可用命令
opencli list

# 以 JSON 格式查看
opencli list -f json

# 以 YAML 格式查看
opencli list -f yaml
```

### 3.2 常用命令示例

```bash
# B 站热门
opencli bilibili hot --limit 10

# 知乎热榜
opencli zhihu hot -f json

# 调用 ChatGPT
opencli chatgpt ask "问题" --timeout 60

# GitHub 操作
opencli gh repo view owner/repo
opencli gh pr list --limit 10

# 诊断工具
opencli doctor
```

### 3.3 输出格式

所有命令支持以下输出格式：

```bash
opencli bilibili hot -f table   # 表格（默认）
opencli bilibili hot -f json    # JSON
opencli bilibili hot -f yaml    # YAML
opencli bilibili hot -f md      # Markdown
opencli bilibili hot -f csv     # CSV
```

---

## 四、Skills 使用指南

### 4.1 什么是 Skills

**Skills** 是 opencli 中定义的可复用能力单元，AI 可以通过 `Skill` 工具调用它们。

### 4.2 Skills 目录结构

```
/Users/busiji/workbot/
├── gpt-web-to/
│   └── SKILL.md          # gpt-web-to 技能定义
├── agents/
│   ├── github-skill.md   # GitHub 技能（工作空间级）
│   └── ...
└── .agents/skills/
    ├── gpt-web-teacher/
    │   └── SKILL.md      # gpt-web-teacher 技能（全局级）
    └── github/
        └── SKILL.md      # GitHub 技能（全局级）
```

### 4.3 现有 Skills 列表

| Skill 名称 | 位置 | 用途 |
|-----------|------|------|
| `gpt-web-to` | `/Users/busiji/workbot/gpt-web-to/` | 调用 ChatGPT 进行教学解释 |
| `github` | `~/.agents/skills/github/` | 操作 GitHub（PR、Issue、Repo） |
| `gpt-web-teacher` | `~/.agents/skills/gpt-web-teacher/` | ChatGPT 教学（旧版） |

### 4.4 调用 Skills 的方式

#### 方式 1：通过 AI 调用

当用户说：
> "用 GPT 老师解释一下 React Virtual DOM"

AI 会自动调用：
```
skill: "gpt-web-to", args: "解释 React Virtual DOM"
```

#### 方式 2：直接使用 opencli 命令

```bash
# gpt-web-to 的底层命令
opencli chatgpt-web ask "问题" --timeout 60 -f md

# github 技能的底层命令
opencli gh pr list --limit 10
opencli gh repo view owner/repo
```

### 4.5 创建新 Skill

**Skill 文件结构**：

```markdown
---
name: skill-name
description: 技能的简短描述
---

# Skill 名称

## 何时使用

描述触发条件。

## 工作流程

1. 步骤一
2. 步骤二
3. 步骤三

## 示例

```bash
opencli xxx command "参数"
```
```

**存放位置**：

- **工作空间级**：`/Users/busiji/workbot/agents/xxx-skill.md`
- **全局级**：`~/.agents/skills/xxx/SKILL.md`

---

## 五、底层命令详解

### 5.1 浏览器命令

#### chatgpt-web

```bash
# 发送问题并获取回答
opencli chatgpt-web ask "问题" --timeout 60 -f md

# 检查状态
opencli chatgpt-web status

# 新建对话
opencli chatgpt-web new

# 读取当前对话
opencli chatgpt-web read

# 发送消息
opencli chatgpt-web send "消息内容"
```

#### 社交媒体

```bash
# B 站
opencli bilibili hot --limit 10
opencli bilibili search --keyword "关键词"
opencli bilibili download "BV 号" --output ./video

# 知乎
opencli zhihu hot -f json
opencli zhihu search --keyword "关键词"
opencli zhihu download "文章 URL" --output ./article

# 小红书
opencli xiaohongshu search --keyword "关键词"
opencli xiaohongshu download "笔记 ID" --output ./media

# Twitter/X
opencli twitter trending
opencli twitter profile --username "用户名"
opencli twitter download "用户名" --limit 20
```

#### 桌面应用

```bash
# Cursor IDE
opencli cursor status
opencli cursor send "消息"
opencli cursor read
opencli cursor composer "代码需求"

# Notion
opencli notion search --query "关键词"
opencli notion read "页面 ID"
opencli notion write --page "页面 ID" --content "内容"

# Discord
opencli discord-app status
opencli discord-app send --channel "频道 ID" --message "消息"
opencli discord-app read --channel "频道 ID"
```

### 5.2 外部 CLI 枢纽

#### GitHub (gh)

```bash
# 仓库信息
opencli gh repo view owner/repo
opencli gh repo clone owner/repo

# PR 管理
opencli gh pr list --repo owner/repo --limit 10
opencli gh pr view PR 号 --repo owner/repo
opencli gh pr create --title "标题" --body "描述"

# Issue 管理
opencli gh issue list --repo owner/repo --limit 10
opencli gh issue view Issue 号 --repo owner/repo

# Actions
opencli gh run list --repo owner/repo
opencli gh run view RunID --repo owner/repo
```

#### Docker

```bash
opencli docker ps
opencli docker images
opencli docker build -t 镜像名 .
opencli docker run -it 镜像名 bash
```

#### kubectl

```bash
opencli kubectl get pods
opencli kubectl get deployments
opencli kubectl apply -f deployment.yaml
```

### 5.3 开发与探索命令

#### explore - 探索网站 API

```bash
# 探索网站，发现 API 端点
opencli explore https://example.com --site mysite

# 查看探索结果
ls .opencli/explore/mysite/
```

#### synthesize - 生成适配器

```bash
# 根据探索结果生成适配器
opencli synthesize mysite

# 生成的文件位置
ls .opencli/clis/mysite/
```

#### generate - 一键生成

```bash
# 探索 → 合成 → 注册 一站式完成
opencli generate https://example.com --goal "获取热门数据"
```

#### cascade - 认证策略探测

```bash
# 自动探测认证策略（PUBLIC → COOKIE → HEADER）
opencli cascade https://api.example.com/data
```

---

## 六、浏览器集成

### 6.1 Chrome 扩展模式（默认）

**前置条件**：

1. 安装 Browser Bridge 扩展
2. Chrome 已登录目标网站
3. 扩展已启用

**使用方式**：

```bash
# 直接使用，默认通过 Chrome 扩展
opencli chatgpt-web ask "问题"
opencli bilibili hot
```

### 6.2 AdsPower 指纹浏览器模式

**前置条件**：

1. AdsPower 客户端已启动
2. API Key 已配置
3. 浏览器配置文件已创建

**配置步骤**：

```bash
# 1. 获取浏览器列表
export ADSPOWER_API_KEY="你的 Key"
curl -H "Authorization: Bearer $ADSPOWER_API_KEY" \
     http://local.adspower.net:50325/api/v2/browser-profile/list

# 2. 设置环境变量
export OPENCLI_BROWSER_BACKEND=adspower
export OPENCLI_BROWSER_PROFILE_ID="浏览器 ID"

# 3. 打开浏览器（可选，opencli 会自动打开）
curl -X POST -H "Authorization: Bearer $ADSPOWER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"profile_id": "浏览器 ID"}' \
     http://local.adspower.net:50325/api/v2/browser-profile/start

# 4. 使用 opencli 命令
opencli chatgpt-web ask "问题" --timeout 60

# 5. 关闭浏览器（测试完成后）
curl -X POST -H "Authorization: Bearer $ADSPOWER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"profile_id": "浏览器 ID"}' \
     http://local.adspower.net:50325/api/v2/browser-profile/stop
```

### 6.3 稳定性测试报告

**测试条件**：
- AdsPower 指纹浏览器
- 10 次复杂问题测试（每个问题>50 字）
- 超时设置 90 秒

**测试结果**：

| 指标 | 数值 |
|------|------|
| 成功率 | 30% (3/10) |
| 超时率 | 70% (7/10) |
| 平均耗时（成功） | ~35 秒 |
| 平均耗时（超时） | ~68 秒 |

**问题根源**：
1. 60 秒超时限制对复杂问题不够
2. CDP 导航超时 30 秒可能过早触发
3. AdsPower 浏览器会话状态可能不稳定

**建议**：
1. 增加超时时间到 120 秒
2. 添加重试机制
3. 确保浏览器会话保持活跃

---

## 七、故障排查

### 7.1 诊断命令

```bash
# 检查 opencli 状态
opencli doctor

# 检查 ChatGPT 状态
opencli chatgpt-web status

# 检查 AdsPower 连接
curl -H "Authorization: Bearer $ADSPOWER_API_KEY" \
     http://local.adspower.net:50325/api/v2/browser-profile/list
```

### 7.2 常见问题

#### 问题 1: "Extension not connected"

**原因**：Browser Bridge 扩展未安装或未启用

**解决**：
1. 打开 Chrome 的 `chrome://extensions`
2. 确保 Browser Bridge 扩展已启用
3. 刷新目标网站页面

#### 问题 2: "No response within 60s"

**原因**：ChatGPT 响应超时

**解决**：
1. 增加超时时间：`--timeout 90`
2. 检查网络连接
3. 检查 ChatGPT 登录状态

#### 问题 3: "Require api-key" (AdsPower)

**原因**：未设置或错误的 API Key

**解决**：
```bash
export ADSPOWER_API_KEY="正确的 Key"
```

#### 问题 4: "CDP command timed out"

**原因**：Chrome DevTools Protocol 命令超时

**解决**：
1. 增加超时时间
2. 重启浏览器
3. 检查浏览器是否卡顿

### 7.3 日志查看

```bash
# 查看 opencli 日志
opencli doctor --verbose

# 查看 AdsPower 日志
# 在 AdsPower 客户端查看
```

---

## 附录

### A. 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLI_BROWSER_BACKEND` | `chrome-extension` | 后端类型 |
| `OPENCLI_BROWSER_PROFILE_ID` | - | AdsPower 浏览器 ID |
| `ADSPOWER_API_KEY` | - | AdsPower API Key |
| `OPENCLI_BROWSER_CONNECT_TIMEOUT` | 30 | 连接超时（秒） |
| `OPENCLI_BROWSER_COMMAND_TIMEOUT` | 45 | 命令超时（秒） |

### B. 项目位置

| 项目 | 路径 |
|------|------|
| opencli 源码 | `/Users/busiji/workbot/opencli/` |
| gpt-web-to Skill | `/Users/busiji/workbot/gpt-web-to/` |
| GitHub Skill | `/Users/busiji/workbot/agents/github-skill.md` |
| 全局 Skills | `~/.agents/skills/` |

---

**文档状态**：草稿中
**下次更新**：根据 opencli 版本更新
