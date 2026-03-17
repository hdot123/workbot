# ClawRouter Git 仓库初始化完成

**日期**: 2026-03-12
**版本**: v2.5.7

## ✅ 已完成的工作

### 1. Git 仓库初始化
- ✅ 在 `/opt/clawrouter` 目录初始化 Git 仓库
- ✅ 创建 `.gitignore` 文件（排除 node_modules, logs, .env, 备份文件等）
- ✅ 创建详细的 `README.md` 文档
- ✅ 初始提交包含以下文件：
  - `.gitignore` - Git 忽略规则
  - `README.md` - 项目文档
  - `docker-compose.yml` - Docker 配置
  - `src/server.js` - 主服务代码（v2.5.7）
  - `src/protocol-adapter.js` - 协议适配器
  - `src/codex-protocol.js` - Codex 协议

### 2. Git 提交信息
```
feat: ClawRouter v2.5.7 初始版本

- 多品牌协议路由服务（智谱、百炼、Voyage）
- Voyage 模型级 fallback（voyage-4 → voyage-4-lite → voyage-4-large）
- SOCKS5 代理支持
- /v1/completions 端点兼容
- 模型别名清理（真实模型映射）
```

### 3. 远程仓库配置
- ✅ GitHub 仓库: https://github.com/hdot123/ClawRouter
- ✅ 添加远程仓库地址到本地配置
- ⚠️ **等待推送**: 需要配置 GitHub 认证

## 🔐 推送到 GitHub 的认证方式（3选1）

### 方式 1: 使用 SSH URL（推荐）

**步骤**:

1. **在 VM 上生成 SSH 密钥**（如果没有）:
   ```bash
   ssh ubuntu@192.168.88.27
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # 按 Enter 使用默认路径，可以设置密码或留空
   ```

2. **将公钥添加到 GitHub**:
   ```bash
   # 查看公钥
   cat ~/.ssh/id_ed25519.pub

   # 复制公钥内容，然后：
   # GitHub → Settings → SSH and GPG keys → New SSH key
   # 粘贴公钥内容并保存
   ```

3. **修改远程仓库 URL 为 SSH**:
   ```bash
   cd /opt/clawrouter
   git remote set-url origin git@github.com:hdot123/ClawRouter.git
   git push -u origin main
   ```

### 方式 2: 使用 Personal Access Token（HTTPS）

**步骤**:

1. **创建 GitHub Token**:
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token (classic)
   - 勾选 `repo` 权限
   - 生成并保存 token（只显示一次）

2. **推送时使用 Token**:
   ```bash
   ssh ubuntu@192.168.88.27
   cd /opt/clawrouter
   git push -u origin main
   # Username: hdot123
   # Password: <粘贴你的 token>
   ```

3. **（可选）保存凭证**:
   ```bash
   git config --global credential.helper store
   # 下次推送时输入一次 token 后会自动保存
   ```

### 方式 3: 使用 GitHub CLI（最简单）

**步骤**:

1. **安装 GitHub CLI**:
   ```bash
   ssh ubuntu@192.168.88.27
   sudo apt update
   sudo apt install gh
   ```

2. **登录 GitHub**:
   ```bash
   gh auth login
   # 选择 GitHub.com
   # 选择 HTTPS
   # 选择 Yes (authenticate with GitHub credentials)
   # 选择 Login with a web browser
   # 复制 one-time code，打开浏览器登录
   ```

3. **推送**:
   ```bash
   cd /opt/clawrouter
   git push -u origin main
   ```

## 📊 当前仓库状态

```bash
# 查看状态
ssh ubuntu@192.168.88.27 "cd /opt/clawrouter && git status"

# 查看提交历史
ssh ubuntu@192.168.88.27 "cd /opt/clawrouter && git log --oneline"

# 查看远程配置
ssh ubuntu@192.168.88.27 "cd /opt/clawrouter && git remote -v"
```

## 🚀 推送后的操作

推送成功后，建议：

1. **在 GitHub 创建分支保护规则**:
   - Settings → Branches → Add rule
   - Branch name pattern: `main`
   - 勾选 "Require pull request reviews before merging"

2. **创建开发分支**:
   ```bash
   git checkout -b develop
   git push -u origin develop
   ```

3. **添加 GitHub Actions（可选）**:
   - 自动化测试
   - 自动化部署
   - 代码质量检查

## 📝 日常维护

### 提交修改
```bash
cd /opt/clawrouter
git add .
git commit -m "描述你的修改"
git push
```

### 查看修改历史
```bash
git log --oneline --graph --all
```

### 回滚到指定版本
```bash
git log  # 找到要回滚的 commit hash
git reset --hard <commit-hash>
git push --force  # 谨慎使用
```

## 🔧 .gitignore 说明

已配置忽略以下内容：
- `node_modules/` - Node.js 依赖
- `logs/` - 日志文件
- `.env` - 环境变量（包含敏感信息）
- `*.bak`, `*.backup*` - 备份文件
- `data/*.json`, `data/*.db` - 数据文件
- `config/api-keys.json`, `config/secrets.json` - 配置文件

## ⚠️ 重要提醒

1. **永远不要提交 `.env` 文件到 Git**（已添加到 .gitignore）
2. **备份文件不会被跟踪**（已添加到 .gitignore）
3. **敏感信息（API Keys）不要提交到 Git**
4. **定期推送到 GitHub 以保持备份**

## 📚 相关文档

- **ClawRouter VM 文档**: `workspace/memory/kb/projects/clawrouter-vm101.md`
- **node-22 代理服务**: `workspace/memory/kb/projects/node-22.md`
- **README.md**: 已上传到仓库根目录

---

**创建者**: Claude (Molt 的 AI 助手)
**创建时间**: 2026-03-12
**GitHub 仓库**: https://github.com/hdot123/ClawRouter
