---
name: rea-codex-review
description: |
  让 rea-bot 在 Claude Code 中通过 codex-plugin-cc 发起只读代码审查。
  本技能只负责 codex 插件链路；链路失败时直接阻塞，不做本地 fallback。
---

# rea-codex-review

## 目的

本技能只负责一件事：

在 Claude Code 中通过 `codex-plugin-cc` 发起只读代码审查，并取回结果。

## 前置条件

- Claude 已启用 `codex@openai-codex` 插件
- 当前会话已注入 `CLAUDE_PLUGIN_DATA`
- Claude 输入框中可见 `/codex:*` 命令

## 标准命令

```text
/codex:setup
/codex:setup --enable-review-gate
/codex:setup --disable-review-gate
/codex:review --wait|--background [--base <ref>] [--scope auto|working-tree|branch]
/codex:review --base main
/codex:adversarial-review --wait|--background [--base <ref>] [--scope auto|working-tree|branch] [focus ...]
/codex:status [job-id] [--wait] [--timeout-ms <ms>] [--all]
/codex:result [job-id]
/codex:cancel [job-id]
/reload-plugins
```

## 命令口径

- `/codex:setup`
  - 检查 `codex-plugin-cc`、本地 `codex` CLI 和认证状态
  - 仅在用户明确要求时才考虑 review gate 开关

- `/codex:review`
  - 普通只读审查
  - 适用于当前 working tree 或 `--base <ref>` 分支对比
  - 不带自定义 focus 文本

- `/codex:adversarial-review`
  - 质疑式只读审查
  - 除普通审查范围外，还可附带 focus 文本，指定要挑战的设计或风险点

- `/codex:status`
  - 查看后台审查任务进度
  - 可按 `job-id` 查询，也可配合 `--wait`、`--timeout-ms <ms>`、`--all`

- `/codex:result`
  - 读取已完成任务的完整结果
  - 无 `job-id` 时取最近结果；有 `job-id` 时取指定结果

- `/codex:cancel`
  - 取消后台审查任务
  - 只用于中止 review / adversarial-review 后台任务

## 排除项

- `/codex:rescue` 不属于本技能范围
- 本技能不把调查、修复或实现任务委托给 Codex
- 本技能只负责 review backend，不负责写入型执行链路

## 结果保存

- 审查任务结果会按 workspace 落盘到本地状态目录
- 优先目录：`CLAUDE_PLUGIN_DATA/state/<workspace-slug>-<hash>/`
- 回退目录：`os.tmpdir()/codex-companion/<workspace-slug>-<hash>/`
- `state.json` 保存 job 索引与配置
- `jobs/<job-id>.json` 保存单次审查结果、状态、threadId、turnId 与 rendered 输出
- `jobs/<job-id>.log` 保存进度日志和最终输出
- `/codex:status` 与 `/codex:result` 都依赖这些本地落盘文件
- 默认最多保留最近 `50` 个 job
- Claude 当前 session 结束时，当前 session 对应的 job 与工件会被清理，因此不能把它当长期审计归档

## 默认工作流

1. 先执行 `/codex:setup`
2. 如果 Claude 看不到 `/codex:*`，执行 `/reload-plugins`
3. 根据范围选择 `/codex:review` 或 `/codex:adversarial-review`
4. 根据任务大小选择 `--wait` 或 `--background`
5. 如需对比分支，显式带上 `--base <ref>`
6. 如果是后台任务，使用 `/codex:status` 跟踪；必要时用 `/codex:cancel` 中止
7. 任务结束后用 `/codex:result` 取回结果
8. 结果必须整理为 `Findings / Evidence / Backend / Conclusion`

## 失败判定

出现以下任一情况，本技能立即判定失败：
- `/codex:setup` 失败
- `/reload-plugins` 后仍无 `/codex:*`
- 审查任务无法启动
- `/codex:result` 无法取回结果

## 失败后的动作

- 立即停止本次审计
- 明确报告 codex 插件链路不可用的真实证据
- 要求先恢复 `codex-plugin-cc`、`/codex:*` 或认证状态后再重新发起审计
- 不切换到 `rea-claude-review`
- 结果中的 `backend` 仍固定写 `codex`

## 一句话职责

**通过 codex-plugin-cc 发起只读代码审查；插件链路失败时直接阻塞并等待 codex 链路恢复。**
