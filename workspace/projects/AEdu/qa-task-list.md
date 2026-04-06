# AEdu QA Task List

## Role
- 本单只记录 QA、验收与发布阻断视角的状态
- 本单从 `dev_done` 接手，管到 `qa_done`
- 本单不替代开发单，也不直接代替 CE 收口

## Overall Status
- `ce_synced`
- 当前口径：内网环境优先于本机环境；本机数据库实例只作备份/应急使用。`APISIX` 现承载 `MySQL` 与 `PostgreSQL` 两类业务面，其中 `PostgreSQL` 业务面通过 `Supabase HTTP http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `PostgreSQL stream apisix.tail5e888.ts.net:5432` 两个入口承载业务主库、向量数据库以及从 `MySQL` 汇入后的基础数据，`MySQL` 业务面则通过 `apisix.tail5e888.ts.net:3306` 承载爬虫采集/落库侧存储；本轮 gaokaozhiyuan 基础库质量门槛 follow-up 的样本覆盖核对来自 `MySQL` 源侧现状，但业务层真源口径落在内网 `PostgreSQL` 业务面。应用层统一只经 APISIX 访问内网服务，`QA-014` 已给出基础数据源侧覆盖的 `Conditional Pass`，`QA-016` 又把正式推演前的硬门槛细化为“补齐 3 张空表、补年份 / 地区 / 批次样本分布说明、完成字段标准化与规则层对接”；内网 MySQL / PostgreSQL 裸库仅作维护，不作应用直连，外网 Supabase 仅承担内网 Supabase 备份；commander 已在 `#32` 追加 follow-up note `227` 记录本轮 QA 边界；既有测试基线仍保持 `112 passed, 0 warnings`，扩展兼容口径仍为 `125 passed, 0 warnings`

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
| QA-012 | Warning 基线复跑确认 | `qa_done` | `qa` | `tests/test_ocr_interface.py`, `tests/test_ocr_event_bridge.py`, `tests/test_ocr_integration.py`, `tests/test_text_main_chain.py`, `tests/test_school_dashboard.py`, `tests/test_feedback_loop.py`, `tests/test_feedback_traceability.py`, `tests/test_obs_compare_dimensions.py`, `tests/test_f8_rollback.py`, `tests/test_f9_scenarios.py`, `tests/test_twin_ingest_contract.py` | 已确认关键测试基线仍为 `112 passed, 44 warnings`；若在此基础上额外纳入 `tests/test_twin_ingest_contract.py`，扩展兼容口径为 `125 passed, 44 warnings`；warning 类型仍全部为 `PytestReturnNotNoneWarning`，无新增失败 | - | 基线已固定；warning 继续按测试形态残余口径维护，不阻塞生命周期 |
| QA-013 | Warning 清理复跑验收 | `qa_done` | `qa` | `tests/test_f8_rollback.py`, `tests/test_school_dashboard.py`, `tests/test_text_main_chain.py`, `tests/test_feedback_loop.py`, `tests/test_obs_compare_dimensions.py`, `tests/test_twin_ingest_contract.py` | 已确认 5 个 warning 目标文件专项复跑 `79/79` 通过且 `0 warnings`；关键基线复跑收敛为 `112/112` 通过且 `0 warnings`；若额外纳入 `tests/test_twin_ingest_contract.py`，扩展兼容口径为 `125/125` 通过且 `0 warnings` | - | warning 残余已清零；后续只维护回归基线与本地真源一致性 |
| QA-014 | gaokaozhiyuan 基础数据覆盖与质量门槛核对 | `qa_done` | `qa` | `APISIX apisix.tail5e888.ts.net:3306 -> MySQL gaokao.china_*`, `AEdu/10_规则与外部数据/02_高考历史数据接入规范.md`, `AEdu/10_规则与外部数据/04_外部数据质量校验规则.md`, `AEdu/09_推演与决策层/10_志愿填报推演框架.md` | 已核对经 APISIX `apisix.tail5e888.ts.net:3306` 暴露的 MySQL `gaokao`.`china_*` 源侧覆盖与质量门槛；同时确认 `APISIX` 当前承载的 `PostgreSQL` 业务面通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 对外提供业务主库、向量数据库与基础数据真源口径，本项不把 MySQL 源侧样本计数误写成 PostgreSQL 行数验收：`china_enrollment_plans`、`china_gaokao_score_rankings`、`china_majors_dictionary`、`china_universities_base` 各有 10 行样本；`china_major_admission_scores`、`china_university_admission_scores`、`china_gaokao_province_scores` 当前为空；内网 MySQL / PostgreSQL 裸库仅作维护，不作应用直连；外网 Supabase 仅承担内网 Supabase 备份；空表不等于设计错误，本轮测试阶段判定为 `Conditional Pass` | `3` 张历史录取 / 省控线表仍为空；正式志愿推演前需补齐数据与样本分布说明 | 后续补充年份/地区样本分布说明，并在正式推演前补齐 admission / province score 数据 |
| QA-015 | cmux 正式运行面验收关口验证 | `qa_done` | `qa` | `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`, `/Users/busiji/.agents/skills/cmux/references/workbot/a1-a9-session-protocol.md`, `workspace/artifacts/cmux-runtime/cmux-assignment.json` | 交付结论: watcher 仅输出候选完成信号，A6 仍需 commander 逐 pane 现场验收；本轮四路 pane 只有在真实交付后才具备收口条件 | - | 转入 CE 同步队列 |
| QA-016 | gaokaozhiyuan 基础库 Conditional Pass 门槛细化 | `qa_done` | `qa` | `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md`, `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/rea-task-list.md` | 已把 `QA-014` 的 `Conditional Pass` 细化为正式门槛：应用层统一只经 APISIX 访问内网服务；其中本轮被核对的是 `apisix.tail5e888.ts.net:3306` 暴露的 MySQL `gaokao`.`china_*`，而业务层真源仍落在通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 暴露的 `PostgreSQL` 业务面；内网 MySQL / PostgreSQL 仅作维护；外网 Supabase 仅承担内网 Supabase 备份；当前 `4/7` 表有样本、`3/7` 表为空；正式志愿推演前必须补齐 `china_major_admission_scores`、`china_university_admission_scores`、`china_gaokao_province_scores`，并补年份 / 地区 / 批次样本分布说明、字段标准化与规则层对接 | `3` 张核心录取 / 省控线表为空，且当前每表仅 `10` 行样本，不足以支撑正式推演 | `#32` 保持 `opened`；正式推演前先补齐数据与样本分布说明，再评估是否进入下一阶段 |

## QA Conclusion Rule
- `qa_done` 必须有可追溯证据
- `blocked` 必须写阻塞原因和解除条件
- 本单如果发现文档、验收材料或 CE 口径与真实实现冲突，可以阻塞正式签收
- 即使 QA 完成，也只允许把 CE 推进到“待文档同步”，不允许直接关单

## Residual Risks
- 当前脚本式测试依赖 `PYTHONPATH=/Users/busiji/workbot`
- 百度 OCR API 主路径：mock / bridge / integration + 真实 API smoke 证据已齐（见 `ocr_qa_evidence.json`）
- 当前 `.venv` 已补装 `pytest`；关键测试集现场已收敛为 `112 passed, 0 warnings`；若额外纳入 `tests/test_twin_ingest_contract.py`，扩展兼容口径为 `125 passed, 0 warnings`；原 `PytestReturnNotNoneWarning` 残余已在本轮清零，不再构成功能或测试形态阻塞
