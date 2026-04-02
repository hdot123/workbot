---
name: rea-claude-review
description: |
  历史保留的本地只读审查技能。
  不作为 rea-bot 的 fallback，也不属于 rea-bot 的正式 backend。
---

# rea-claude-review

## 目的

本技能只负责一件事：

在用户明确点名、且不要求走 rea-bot 正式审计口径时，由 Claude 直接完成本地代码审查和状态审计。

## 边界

- `rea-bot` 不允许调用本技能替代 `rea-codex-review`
- 正式首轮审计仍必须走 `rea-codex-review`
- 本技能不产出 rea-bot 的正式 backend 口径

## 真实输入

- `git diff --stat`
- `git diff`
- 指定实现文件
- 指定测试文件
- 指定 task-list / 文档 / 验收文件
- 最小必要验证命令结果

## 默认工作流

1. 读取 `git diff --stat`
2. 读取 `git diff` 或用户点名文件
3. 读取相关测试文件和验收材料
4. 如有必要，运行最小必要验证
5. 识别 `P0 / P1 / P2` 问题
6. 核对代码、测试、状态文件是否一致
7. 输出 `Findings / Evidence / Backend / Conclusion`

## 审查重点

- 回归风险
- 边界条件
- 异常与降级路径
- 接口或数据结构破坏
- 缺测试
- task-list / 文档 / 验收文件 / CE 状态漂移

## 输出口径

- `Findings`: 先问题，后结论
- `Evidence`: 只写真实文件、命令和结果
- `Backend`: 固定写 `claude`
- `Conclusion`: 只写 `允许继续`、`需补同步后复核`、`不允许收口`

## 一句话职责

**仅在用户明确点名且不走 rea-bot 正式审计口径时，使用本地 diff、文件阅读和最小验证完成代码审查与状态审计。**
