# AEdu REA Task List

## Role
- 本单只记录 `rea-bot` 的 Review / Examine / Audit 状态
- 本单不替代开发单、QA 单或 Doc 单
- 本单用于形成真实性、稳定性和一致性审查结论

## Overall Status
- `ce_synced`
- 当前口径：当前无活跃审计卡；阶段二主链事实、文档和 CE 已基本对齐；百度 OCR 已完成 baidu-only 收口且 `#56` 已按退役口径关闭，并已补齐真实 API smoke 证据；阶段三试点实施材料、反馈闭环可追溯性与观察层准入审计已形成结论，阶段四 `#32` 准入条件也已复核为“文档与准入支撑齐备、但真实实现尚未启动”；本轮 `REA-010` 已完成全代码与 CE opened 落点总审查，确认 `#29/#32` 仅作为阶段锚点保留，`#28/#30/#31/#33` 继续承接生命周期与历史追溯；本轮 `REA-011` 已进一步确认 `44` 个 warning 全部源自 5 个测试文件中被 pytest 收集到、且显式 `return tuple` 的顶层 `test_*` 函数，属于测试形态残余，不阻塞生命周期

## Canonical Status Model
- `todo`: 已登记，未开始
- `in_progress`: 已开工，有明确 owner
- `blocked`: 有阻塞，当前不能推进
- `dev_done`: 开发完成，待 QA 接手
- `qa_done`: QA 结论已形成
- `doc_synced`: 文档与验收材料已同步
- `ce_synced`: CE 已同步
- `done`: 正式收口完成

## Intake Rule
- 当代码、测试、task-list、文档或 CE 之间存在不一致时，进入本单
- 当需要 CE 同步前真实性复核时，进入本单
- 本单可以阻塞“正式收口”，但不能越权直接写 `done`

## Files Under REA
- `app/models/*.py` 中与 AEdu 第一阶段最小闭环相关实现
- `tests/test_text_main_chain.py`
- `tests/test_f8_rollback.py`
- `tests/test_f9_scenarios.py`
- `tests/test_ocr_event_bridge.py`
- `tests/test_ocr_integration.py`
- `workspace/projects/AEdu/dev-task-list.md`
- `workspace/projects/AEdu/qa-task-list.md`
- `workspace/projects/AEdu/doc-task-list.md`
- `workspace/projects/AEdu/rea-task-list.md`
- `workspace/projects/AEdu/ce-sync-plan.md`
- `AEdu/03_教材标准表/samples/validation_report.json`
- `AEdu/03_教材标准表/samples/acceptance_conclusion.json`
- `AEdu/00_文档状态总表.md`
- `AEdu/01_战略与总纲/08_项目阶段目标与里程碑.md`

## Task Board

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| REA-001 | AEdu 主链实现真实性复核 | `qa_done` | `rea` | `app/models/*.py`, `tests/test_text_main_chain.py`, `tests/test_f8_rollback.py`, `tests/test_f9_scenarios.py` | 文本主链、GRAPH 回滚和 F9 场景已跑通 | - | 作为 CE 同步前事实基线 |
| REA-002 | 百度 OCR 主路径稳定性与运行前提复核 | `done` | `rea` | `app/models/ocr_interface.py`, `app/models/ocr_event_bridge.py`, `tests/test_ocr_interface.py`, `tests/test_ocr_event_bridge.py`, `tests/test_ocr_integration.py`, `scripts/ocr_8_samples.py`, `scripts/ocr_textbook.py`, `AEdu/03_教材标准表/samples/ocr_qa_evidence.json` | 百度 OCR 已完成 baidu-only 收口：provider 入口、教材图片/PDF 脚本与 OCR 测试证据已对齐；OCR 自动化测试链本轮复跑 `26/26` 通过；2026-04-02 已使用系统环境变量中的百度 OCR 凭据对样例图 `01_封面.png` 执行真实 API smoke，结果 `event_status=success`、`review_needed=false`、`overall_confidence=0.9826` | - | 审计结论已形成：真实 API smoke 不再是外部前提；后续只维护 OCR 正式主路径证据与 CE 引用一致性 |
| REA-003 | task-list / 验收文件 / 项目文档一致性审计 | `ce_synced` | `rea` | 三张 task-list, `acceptance_conclusion.json`, `00_文档状态总表.md`, `08_项目阶段目标与里程碑.md` | `validation_report.json`、`acceptance_conclusion.json`、阶段文档与三张 task list 已对齐到 `2026-04-02` 事实 | - | 转入阶段三文档一致性守护 |
| REA-004 | CE 同步前真实性关口审计 | `ce_synced` | `rea` | `ce-sync-plan.md`, CE issues `#28`, `#30`, `#33`, `#37-69` | 已基于本地验证证据执行 CE 同步；`#56` 已改写为本地 runner 退役/收口处置项，不再表述为正式主路径阻塞 | - | 继续盯住 `#56` 生命周期处置是否与本地真源一致 |

## Next Round Intake

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| REA-005 | 阶段三观察层准入真实性审计 | `done` | `rea` | `AEdu/01_战略与总纲/08_项目阶段目标与里程碑.md`, `AEdu/08_观察层与产品层/07_对比维度与观察口径.md`, `AEdu/08_观察层与产品层/08_家长周报月报设计.md`, `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/doc-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md`, `app/models/obs_models.py`, `app/models/school_dashboard.py`, `app/models/compare_dimension.py`, `app/models/feedback_event.py`, `tests/test_text_main_chain.py`, `tests/test_school_dashboard.py`, `tests/test_obs_compare_dimensions.py`, `tests/test_feedback_loop.py`, `tests/test_feedback_traceability.py` | 已确认阶段三当前实现仍停在观察层增强期边界：家长周报/月报、老师端详情、班级/学校看板、对比维度、反馈闭环与最小问题库/复盘口径均与 OBS-007/008/009/010 及 STR-008 阶段三目标一致；未发现阶段四干预动作库、InterventionSimulator、风险预测模型、志愿填报推演等真实实现落地；同时已修正 STR-008 中“阶段三启动准备 / `#56` opened”旧口径 | - | 允许继续按阶段三主线推进，并转入常态生命周期维护 |
| REA-006 | 反馈闭环与运营指标可追溯性审计 | `done` | `rea` | `AEdu/08_观察层与产品层/10_产品交互与反馈闭环.md`, `AEdu/12_实施与试点运营/06_试点反馈与优化闭环.md`, `AEdu/12_实施与试点运营/07_运营指标与复盘机制.md`, `AEdu/12_实施与试点运营/08_试点阶段问题库.md`, `app/models/feedback_event.py`, `tests/test_feedback_loop.py`, `tests/test_feedback_traceability.py` | 已确认原实现只覆盖“反馈记录 + 路由 + 状态”，本轮补齐 `PilotProblem` 问题库对象、`FeedbackTraceabilitySnapshot` 指标快照、`FeedbackTraceabilityBuilder` 周复盘汇总能力；反馈链联合回归 `20/20` 通过，已可支撑反馈处理完成率 / 问题关闭率 / 干预执行回填率等最小可追溯口径 | - | 允许继续推进阶段三 commander 生命周期同步，并转入 `REA-005` 阶段三观察层准入真实性审计 |
| REA-007 | OCR runner 退役/收口口径审计 | `done` | `rea` | `app/models/ocr_interface.py`, `tests/test_ocr_integration.py`, GitLab CE `#56`, `workspace/projects/AEdu/ce-sync-plan.md` | 当前已确认代码与脚本均为 baidu-only，OCR 测试复核 `26/26` 通过；`#56` 已补退役关单评论并正式关闭 | - | 审计结论已形成：可按策略变更退役关单，不再保留假阻塞 |
| REA-008 | 试点实施材料与观察层价值口径审计 | `done` | `rea` | `AEdu/12_实施与试点运营/02_试点学校实施方案.md`, `AEdu/12_实施与试点运营/04_老师培训与操作手册.md`, `AEdu/12_实施与试点运营/05_家长使用引导.md`, `AEdu/08_观察层与产品层/02_家长端展示规则.md`, `AEdu/08_观察层与产品层/03_老师端展示规则.md`, `AEdu/08_观察层与产品层/09_学校班级看板设计.md`, `tests/test_text_main_chain.py`, `tests/test_school_dashboard.py`, `tests/test_feedback_loop.py` | 已确认试点实施/培训/家长引导文档与 OBS-002/003/009/010 的真实实现边界一致；家长周报/月报、老师学生详情、班级/学校看板、反馈闭环本轮联合复跑 `56/56` 通过；同时纠正 `QA-006/007` 中旧的不存在测试文件引用，回写到真实证据路径 | - | 已收口；阶段三后续转入反馈追溯与观察层准入审计 |
| REA-009 | 阶段四准入条件与 `#32` 生命周期审计 | `done` | `rea` | `AEdu/09_推演与决策层/*.md`, `AEdu/11_系统架构与工程实现/32_推演引擎服务设计.md`, `AEdu/11_系统架构与工程实现/33_风险预测服务设计.md`, `AEdu/11_系统架构与工程实现/34_SIM最小验收矩阵.md`, `AEdu/00_导航与管理/SIM模块级开发准入评审单.md`, `app/models/compare_dimension.py`, `app/models/obs_models.py`, `app/models/feedback_event.py`, `tests/test_obs_compare_dimensions.py`, `tests/test_text_main_chain.py`, `tests/test_feedback_traceability.py`, `workspace/projects/AEdu/ce-sync-plan.md`, GitLab CE `#32` | 已确认 SIM 设计/准入文档齐备，且 `NAV-009` 在 `2026-03-22` 允许进入首轮骨架开发；但当前仓库仍未出现独立 `SIM / risk prediction / shadow simulation / InterventionSimulator` 实现文件与测试入口，`ARCH-034` 要求的 3 组端到端样例跑通记录也未落地；现有 `intervention_before_after` 维度、`intervention_reviews` 字段与干预回填率仅属于观察层/反馈追溯口径，不构成阶段四真实实现 | - | 审计结论已形成：`#32` 继续作为未来阶段锚点保留，CE 已补 `note 214`；未进入真实实现前不登记阶段四开发任务 |
| REA-010 | 全代码与 CE opened 落点总审查 | `done` | `rea` | `app/models/*.py`, `tests/*.py`, `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/doc-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md`, GitLab CE `#28/#29/#30/#31/#32/#33` | 已由 `rea-bot` 使用 codex 完成首轮全代码审查；确认四张 task-list 均为 `ce_synced` 且无活跃卡，`app/models/` 与 `tests/` 中不存在阶段四 SIM 真实实现/测试入口；CE 落点分类明确为 `#29/#32` 仅阶段锚点，`#28/#30/#31/#33` 继续承接生命周期或历史追溯；随后已在当前 `.venv` 补装 `pytest` 并现场复跑关键测试集，结果 `112 passed, 44 warnings`，未发现会推翻首轮结论的新阻断差异 | 当前残余风险已从“缺 pytest”收敛为“老测试仍保留 tuple return 写法，触发 `PytestReturnNotNoneWarning` 44 次” | 允许 commander 继续维持本地 task-list 守护态；若要进一步清洁测试形态，后续可登记一次专门的 warning 清理任务 |
| REA-011 | Warning 来源与修改边界审计 | `done` | `rea` | `tests/test_text_main_chain.py`, `tests/test_school_dashboard.py`, `tests/test_feedback_loop.py`, `tests/test_obs_compare_dimensions.py`, `tests/test_f8_rollback.py`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md` | 已确认 `44` 个 `PytestReturnNotNoneWarning` 全部来自 5 个测试文件中被 pytest 收集到、且显式 `return tuple` 的 `44` 个顶层 `test_*` 函数；helper / fixture / wrapper 的合法返回不在本轮 warning 来源内 | - | 允许按“测试形态残余、非功能失败”口径继续维护；若未来清理 warning，仅允许改测试函数返回值写法，不改业务代码 |

## REA Rule
- `rea` 只做审查、复核和审计，不承担主实现
- `blocked` 必须写清楚是实现阻塞、环境阻塞还是口径阻塞
- 发现“代码已完成但状态文件未同步”时，应阻塞正式收口
- 发现“QA 已完成但 CE 仍写待开发”时，应要求先同步再关单

## Conclusion Rule
- 本单的结论只分为：`允许继续`、`需补同步后复核`、`不允许收口`
- 当前默认结论：`允许继续`
