# Projects Canonical Index

## Purpose
- `projects/` 是总记忆系统中的项目 canonical 入口层。
- 每个文件描述一个项目或项目域的稳定事实、边界和派生规则。
- 项目 canonical 服从 `../global/` 中的总规则，不与总规则并列竞争。

## Active Project Canonical
- `workbot.md`
- `AEdu.md`
- `platform-capabilities.md`

## Rules
- 项目规范只能从总记忆系统派生，不能自立为第二套总系统。
- 项目运行材料进入 `../../projects/**`，不是这里。
- 项目外部来源材料进入 `../../docs/**`，不是这里。

## Compatibility
- 旧入口 `../global/projects/` 已于 2026-04-11 降级为兼容跳转层。
- 新增或更新项目 canonical 时，只修改当前目录，不再写入 `global/projects/`。
