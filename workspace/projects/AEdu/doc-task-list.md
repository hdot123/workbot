# AEdu Doc Task List

## Role
- 本单只记录文档同步、验收材料同步和 CE 同步准备
- 本单不替代开发结论与 QA 结论
- 本单管到 `doc_synced`，不直接替 CE 宣布 `done`

## Overall Status
- `ce_synced`
- 当前口径：当前无活跃文档同步卡；阶段二文档、验收材料与 CE 已同步；DOC-001 ~ DOC-008 已完成收口；OBS Contract 5 文档与 OPS 同步 4 文档已通过 6+1 评审并冻结为"已冻结"；DOC-009/010/011/012/013/014/015 已完成；`#56` 已按退役口径关闭；百度 OCR 真实 API smoke 已补证；本轮 warning 清理已完成，本地真源应以 `112 passed, 0 warnings` / `125 passed, 0 warnings` 口径维护，后续只维护阶段三生命周期与阶段边界引用一致性

## Canonical Status Model
- `todo`: 已登记，未开始
- `in_progress`: 已开工，有明确 owner
- `blocked`: 有阻塞，当前不能推进
- `dev_done`: 开发完成，待 QA 接手
- `qa_done`: QA 结论已形成
- `doc_synced`: 文档与验收材料已同步
- `ce_synced`: CE 已同步
- `done`: 正式收口完成

## Files Under Doc
- `AEdu/00_文档状态总表.md`
- `AEdu/01_战略与总纲/08_项目阶段目标与里程碑.md`
- `AEdu/03_教材标准表/samples/acceptance_conclusion.json`
- `workspace/projects/AEdu/dev-task-list.md`
- `workspace/projects/AEdu/qa-task-list.md`
- `workspace/projects/AEdu/doc-task-list.md`
- `workspace/projects/AEdu/ce-sync-plan.md`

## Task Board

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| DOC-001 | 同步项目阶段判断文档 | `doc_synced` | `doc` | `AEdu/01_战略与总纲/08_项目阶段目标与里程碑.md` | 审计结论已形成 | 已完成同步 | 后续按统一口径维护 |
| DOC-002 | 同步文档状态总表 | `doc_synced` | `doc` | `AEdu/00_文档状态总表.md` | 审计结论已形成 | 已完成同步 | 后续按统一口径维护 |
| DOC-003 | 同步验收结论文件的 validation 摘要 | `doc_synced` | `doc` | `AEdu/03_教材标准表/samples/acceptance_conclusion.json` | `validation_report.json` 已更新为 `2026-04-02`，已与 `acceptance_conclusion.json` 对齐 | - | 交给 QA 复核后形成正式 `qa_done` 结论 |
| DOC-004 | 把开发单切到统一状态模型 | `doc_synced` | `doc` | `workspace/projects/AEdu/dev-task-list.md` | 本次已改写 | - | 后续只按统一状态链维护 |
| DOC-005 | 把 QA 单切到统一状态模型 | `doc_synced` | `doc` | `workspace/projects/AEdu/qa-task-list.md` | 本次已改写 | - | 后续只按统一状态链维护 |
| DOC-006 | 维护文档同步单自身 | `doc_synced` | `doc` | `workspace/projects/AEdu/doc-task-list.md` | 本次已改写 | - | 持续作为 Doc 执行入口 |
| DOC-007 | 产出 CE 状态同步计划 | `doc_synced` | `doc` | `workspace/projects/AEdu/ce-sync-plan.md` | 本次已落本地计划 | - | 交给指挥官按计划执行 API 更新 |
| DOC-008 | 执行 CE 正式同步 | `ce_synced` | `doc` | CE issues `#28`, `#30`, `#31`, `#33`, `#34-69` | 已按本地计划完成 CE API 评论与关单/保留 opened 同步；`#56` 已改写为本地 runner 退役/收口处置并正式关闭 | - | 转入阶段三文档同步入口 |

## Next Round Intake

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| DOC-009 | 同步阶段三观察层增强期任务入口 | `doc_synced` | `doc` | AEdu/08_观察层与产品层/02_家长端展示规则.md, AEdu/08_观察层与产品层/03_老师端展示规则.md, AEdu/08_观察层与产品层/08_家长周报月报设计.md, AEdu/08_观察层与产品层/09_学校班级看板设计.md, AEdu/08_观察层与产品层/10_产品交互与反馈闭环.md | OBS Contract 5 文档已冻结为"已冻结"（2026-04-02 评审通过） | - | 交给 DEV 启动 DEV-008/009/010/012，QA 启动 QA-006 |
| DOC-010 | 对齐试点实施与观察层输出文档 | `doc_synced` | `doc` | AEdu/12_实施与试点运营/02_试点学校实施方案.md, AEdu/12_实施与试点运营/04_老师培训与操作手册.md, AEdu/12_实施与试点运营/05_家长使用引导.md, AEdu/12_实施与试点运营/07_运营指标与复盘机制.md | OPS 同步 4 文档已冻结为"已冻结"（2026-04-02 评审通过），与 OBS Contract 口径对齐 | - | 交给 DEV 启动阶段三开发任务 |
| DOC-011 | 维护 OCR runner 阻塞与阶段三任务的 CE 映射 | `ce_synced` | `doc` | `workspace/projects/AEdu/ce-sync-plan.md`, `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md` | #31 与 #56 口径已统一：正式 OCR 主路径固定为百度 OCR API only；本轮代码与脚本已切 baidu-only，`#56` 标题/描述已改写并按退役口径关闭；DEV-012 `dev_done`，QA-010 `qa_done` | - | OCR runner 生命周期映射已完成收口，后续只维护阶段单引用一致性 |
| DOC-012 | 同步观察层反馈闭环与验收口径 | `ce_synced` | `doc` | `AEdu/08_观察层与产品层/10_产品交互与反馈闭环.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md`, `AEdu/08_观察层与产品层/qa_008_feedback_samples.json`, `AEdu/08_观察层与产品层/feedback_boundary_rules.md` | 反馈闭环验收口径已固化：4 种 feedback_type、4 种 route_destination、MVP 范围已实现；QA-008 已完成（本轮收口复核 34/34 pytest 通过），12 个验收样例固化，8 条回流断言固化，审计边界已验证；6+1 评审正式结论已在 ce-sync-plan 中记录为“评审通过”；`#31` 已补生命周期评论（note 206） | - | CE 生命周期已同步；后续只维护阶段三主线引用一致性 |
| DOC-013 | 同步反馈闭环可追溯与运营复盘口径 | `ce_synced` | `doc` | `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md` | 已把 REA-006 审计结论、DEV-016 / QA-011 证据和反馈追溯口径回写到本地真源；当前口径明确为“反馈闭环不仅可路由，也可形成问题库与指标快照”；`#31` 已补生命周期评论（note 206） | - | CE 生命周期已同步；后续只维护阶段三主线引用一致性 |
| DOC-014 | Warning 收口口径准备 | `doc_synced` | `doc` | `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md` | 已复核本地真源：`qa-task-list.md`、`rea-task-list.md`、`ce-sync-plan.md` 对 `44` 个 `PytestReturnNotNoneWarning` 的表述已足够准确；warning 定位为测试形态残余、非功能失败，推荐 CE 说明文案已准备 | - | 后续如需对外说明，可直接复用“非功能失败、属测试形态残余”的标准表述 |
| DOC-015 | Warning 清理收口口径回写 | `doc_synced` | `doc` | `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/doc-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md` | 已按 QA-013 / REA-012 结果把本地真源从 warning 残余口径收敛到“专项 `79/79`、关键基线 `112/112`、扩展兼容 `125/125` 均 `0 warnings`”；并明确本轮无需新增 CE 生命周期评论 | - | 后续如需对外说明，可直接复用“测试形态清洁完成、非生命周期变化”的标准表述 |

## Doc Rule
- `doc_synced` 的前提是：指定文档已与真实实现和 QA 证据对齐
- 本单如果发现开发、QA、文档三者冲突，优先保留冲突并上报
- 不把“本地可跑通”直接改写成“正式验收通过”
- Doc 同步要继续写回同一张 CE issue，不能因为开发完成而另起正式任务
- `doc_synced` 以后仍由指挥官在同一张 CE issue 上执行最终 `ce_synced` / `done`
