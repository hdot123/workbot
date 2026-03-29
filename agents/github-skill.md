# opencli GitHub Skill

> 通过 gh CLI 和浏览器自动化操作 GitHub

---

## 能力说明

本技能提供以下 GitHub 相关能力：

### 1. gh CLI 透传（推荐）

通过 `opencli gh ...` 透传所有 GitHub CLI 命令：

```bash
# PR 管理
opencli gh pr list --limit 10
opencli gh pr view <PR 号>
opencli gh pr create --title "标题" --body "描述"
opencli gh pr merge <PR 号> --merge

# Issue 管理
opencli gh issue list
opencli gh issue view <Issue 号>
opencli gh issue create --title "标题" --body "描述"

# 仓库操作
opencli gh repo view
opencli gh repo clone <owner>/<repo>
opencli gh repo create <repo-name>

# Actions
opencli gh run list
opencli gh run view <run-id>
opencli gh run watch <run-id>

# Code Search
opencli gh code search "关键词" --limit 20
```

### 2. 浏览器自动化（待开发）

用于获取网页数据：

- `github notifications` - 获取通知
- `github dashboard` - 获取动态
- `github profile` - 获取用户主页信息

---

## 使用流程

### 前置条件

```bash
# 1. 安装 gh CLI（如未安装）
brew install gh

# 2. 登录 GitHub
gh auth login
```

### 示例用法

```bash
# 查看我的 PR
opencli gh pr list --author @me

# 查看指定 PR 详情
opencli gh pr view 123 --json title,body,comments

# 创建新 Issue
opencli gh issue create --title "Bug: 某某功能异常" --body "复现步骤：..."

# 查看最近的 CI 运行状态
opencli gh run list --limit 5
```

---

## AI 调用指南

当用户请求与 GitHub 相关的操作时：

1. **优先使用 gh CLI 透传** - 功能最全、最稳定
2. **浏览器模式** - 仅用于 gh CLI 不支持的网页数据获取

### 典型场景

| 用户需求 | 推荐命令 |
|---------|---------|
| 查看/管理 PR | `opencli gh pr ...` |
| 查看/管理 Issue | `opencli gh issue ...` |
| 查看仓库信息 | `opencli gh repo view` |
| 检查 CI 状态 | `opencli gh run list` |
| 获取 GitHub 通知 | （待开发：浏览器模式） |
| 访问 GitHub 网页 | （待开发：浏览器模式） |

---

## 故障排查

### 问题 1: "gh: command not found"

```bash
# 安装 gh
brew install gh  # macOS
sudo apt install gh  # Ubuntu
```

### 问题 2: "authentication failed"

```bash
# 重新登录
gh auth logout
gh auth login
```

---

## 扩展开发

如需添加浏览器适配器（获取通知、Dashboard 等），参考：

1. [CLI-EXPLORER.md](./CLI-EXPLORER.md) - 适配器开发指南
2. 运行 `opencli explore https://github.com --site github` 自动探测

---

**版本**: V1.0
**最后更新**: 2026-03-23
**维护人**: opencli 开发团队
