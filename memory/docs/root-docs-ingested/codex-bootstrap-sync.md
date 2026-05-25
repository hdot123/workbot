# Codex 启动同步说明

## 必须先做的事

如果你是一个已经打开仓库的 Codex 会话，**不要直接继续工作**。

你必须先同步仓库最新内容，否则你看不到最新的交接文档与治理指令。

### 第一步：同步仓库

优先执行：

```bash
git pull --ff-only
```

如果本地有未提交改动，不适合直接 pull，则至少执行：

```bash
git fetch --all
```

然后确认当前分支已经包含最新提交。

---

## 同步后必须阅读的文件

同步完成后，先阅读以下文件，再开始工作：

1. `docs/codex-memory-governance-instructions.md`
2. `docs/codex-session-handoff-2026-04-11.md`
3. `memory/kb/global/memory-router-design-v2.1.1.md`

---

## 当前阶段限制

当前阶段：

- 先整理记忆文档系统规范
- 不准先接 hook
- 不准先扩 runtime
- 不准让外部系统成为项目真相源

如果你还没同步仓库，就不要继续做实现判断。

---

## 一句话

**先 git pull，再读治理文档，再开始工作。**
