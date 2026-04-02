# AEdu QA Task List

## Role
- 本单只记录 QA、验收与发布阻断视角的状态
- 本单从 `dev_done` 接手，管到 `qa_done`
- 本单不替代开发单，也不直接代替 CE 收口

## Overall Status
- `ce_synced`
- 当前口径：当前无活跃 QA 执行卡；阶段二核心路径已完成 QA 与 CE 同步，QA-001 ~ QA-005 保持 `qa_done` 证据状态；OBS Contract 5 文档与 OPS 4 文档已通过 6+1 评审并冻结；QA-006/007/008/010/011 已完成，`QA-009 / #56` 已按退役口径完成生命周期收口；百度 OCR 真实 API smoke 已补证，当前 QA 侧无新增阻塞，仅维护阶段三主线生命周期一致性

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
- 只有当开发侧达到 `dev_done`，任务才进入本单
- QA 可以写 `qa_done`，不能越权写 `done`
- QA 发现阻塞时，直接改为 `blocked` 并写清原因
- QA 进度要续写到同一张 CE issue，不新开 QA 替代单

## Files Under QA
- `AEdu/03_教材标准表/samples/*`
- `AEdu/scripts/validate_kb_closure.py`
- `app/models/*.py` 中与 AEdu 第一阶段最小闭环相关文件
- `tests/test_text_main_chain.py`
- `tests/test_f8_rollback.py`
- `tests/test_f9_scenarios.py`
- `tests/test_ocr_event_bridge.py`
- `tests/test_ocr_integration.py`

## Task Board

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| QA-001 | KB 闭环校验可复现性 | `qa_done` | `qa` | `AEdu/03_教材标准表/samples/*`, `AEdu/scripts/validate_kb_closure.py` | `validate_kb_closure.py --verbose` 在 `2026-04-02` 返回 `pass` | - | 交给 Doc 同步验收材料 |
| QA-002 | 文本主链最小 E2E 冒烟 | `qa_done` | `qa` | `tests/test_text_main_chain.py` | `8/8` pytest 通过（F6/F7/F8/F10 各 2 个） | - | 可交付 QA 复核 |
| QA-003 | GRAPH 回滚与 F9 主链场景 | `qa_done` | `qa` | `tests/test_f8_rollback.py`, `tests/test_f9_scenarios.py` | `14/14` pytest 通过（7 个回滚 +3 个场景 + 包装测试） | - | 可交付 QA 复核 |
| QA-004 | 百度 OCR 主路径与 OCR 集成路径 | `qa_done` | `qa` | `tests/test_ocr_interface.py`, `tests/test_ocr_event_bridge.py`, `tests/test_ocr_integration.py`, `app/models/ocr_interface.py`, `scripts/ocr_8_samples.py`, `scripts/ocr_textbook.py`, `AEdu/03_教材标准表/samples/ocr_qa_evidence.json` | 百度 provider 导入与配置、OCR bridge 与集成路径证据已复核；OCR 自动化测试链本轮复跑 `26/26` 通过；2026-04-02 已使用系统环境变量中的百度 OCR 凭据对样例图 `01_封面.png` 执行真实 API smoke，结果 `event_status=success`、`review_needed=false`、`overall_confidence=0.9826` | - | 可进入 CE 同步；后续只维护 OCR 正式主路径证据引用一致性 |
| QA-005 | 正式 QA 签收包 | `qa_done` | `qa` | `validation_report.json`, `acceptance_conclusion.json`, 三张 task list | 验收材料已同步 (对齐到 2026-04-02)，TWIN/GRAPH/OBS 主链测试证据已复核 | - | 可进入 CE 同步 |

## Next Round Intake

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| QA-006 | 观察层三端输出 contract 与降级场景复核 | `qa_done` | `qa` | `tests/test_text_main_chain.py`, `tests/test_school_dashboard.py`, `tests/test_obs_compare_dimensions.py`, `app/models/obs_models.py`, `app/models/compare_dimension.py`, `AEdu/08_观察层与产品层/qa_006_conclusion.md` | QA-006 初版 `partial_pass_with_blocking` 结论已被 DEV-009/013 后续实现解除；当前真实复核证据以 `tests/test_text_main_chain.py`、`tests/test_school_dashboard.py`、`tests/test_obs_compare_dimensions.py` 为准，contract 与降级场景已完成收口 | - | 转入 CE 同步队列 |
| QA-007 | 周报/月报与学生详情最小 E2E 冒烟 | `qa_done` | `qa` | `tests/test_text_main_chain.py`, `app/models/obs_models.py` | 周报/月报与学生详情最小 E2E 冒烟通过；`ParentWeeklyReport / ParentMonthlyReport / TeacherStudentDetail / ExplanationBlock / ActionSuggestion / FeedbackEntry` 的真实证据落在 `tests/test_text_main_chain.py` 的 DEV-008/009 段；本轮 REA-008 审计联合复跑 `56/56` 通过 | - | 转入 CE 同步队列 |
| QA-008 | 班级看板聚合与反馈闭环回归 | `qa_done` | `qa` | `tests/test_school_dashboard.py` (新增), `tests/test_feedback_loop.py` (新增), `AEdu/08_观察层与产品层/qa_008_feedback_samples.json`, `AEdu/08_观察层与产品层/feedback_boundary_rules.md` | 班级看板聚合规则与反馈闭环分流回归通过；本轮收口复核实际 34/34 pytest 通过，无 P0/P1 阻塞，4 种 feedback_type 分流正确，12 个验收样例固化，8 条回流断言固化，审计边界已验证 | - | 转入 CE 同步，后续由 commander 维护 #31 生命周期 |
| QA-009 | 本地 OCR runner backend 真链路复核 | `done` | `qa` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py`, `app/models/ocr_interface.py` | GitLab CE `#56` 已按退役口径关闭；代码与脚本已切为 baidu-only，本项不再作为正式主线路径验证，按策略变更完成生命周期收口 | - | 生命周期已收口；若未来重启本地 runner 目标，再登记新任务 |
| QA-010 | 家长端周报/月报解释对象 contract 复核 | `qa_done` | `qa` | `tests/test_text_main_chain.py` (DEV-008 测试段), `app/models/obs_models.py` | ExplanationBlock/ActionSuggestion/FeedbackEntry 与 OBS-008/OBS-002 一致性复核通过 (9/9 项 pass)，并已写入 `#31` 生命周期评论（note 206） | - | 生命周期已同步；后续只维护阶段三主线引用一致性 |
| QA-011 | 反馈闭环可追溯指标与问题生命周期复核 | `qa_done` | `qa` | `tests/test_feedback_traceability.py`, `tests/test_feedback_loop.py`, `app/models/feedback_event.py` | 已复核 `PilotProblem` 问题生命周期、反馈提交率/处理完成率/问题关闭率/干预执行回填率计算与周复盘汇总能力；反馈链联合回归 `20/20` 通过，无新增 P0/P1 阻塞，并已写入 `#31` 生命周期评论（note 206） | - | 生命周期已同步；后续只维护阶段三主线引用一致性 |

## QA Conclusion Rule
- `qa_done` 必须有可追溯证据
- `blocked` 必须写阻塞原因和解除条件
- 本单如果发现文档、验收材料或 CE 口径与真实实现冲突，可以阻塞正式签收
- 即使 QA 完成，也只允许把 CE 推进到“待文档同步”，不允许直接关单

## Residual Risks
- 当前脚本式测试依赖 `PYTHONPATH=/Users/busiji/workbot`
- 百度 OCR API 主路径：mock / bridge / integration + 真实 API smoke 证据已齐（见 `ocr_qa_evidence.json`）
- 当前 `.venv` 已补装 `pytest`，并已现场复跑关键测试集：`112 passed`；当前残余不是缺测试依赖，而是若干老测试仍保留“返回 tuple”写法，现场复跑出现 `44` 个 `PytestReturnNotNoneWarning`
