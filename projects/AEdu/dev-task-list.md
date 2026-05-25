# AEdu Dev Task List

## Role
- 本单只记录开发执行状态
- 本单管到 `dev_done`，不负责宣布 `qa_done` 或 `done`
- bot 不自己维护本单状态；状态由指挥官统一回写

## Overall Status
- `ce_synced`
- 当前口径：内网环境优先于本机环境；本机数据库实例只作备份/应急使用。`APISIX` 现承载 `MySQL` 与 `PostgreSQL` 两类业务面，其中 `PostgreSQL` 业务面通过 `Supabase HTTP http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `PostgreSQL stream apisix.tail5e888.ts.net:5432` 两个入口承载业务主库、向量数据库以及从 `MySQL` 汇入后的基础数据，`MySQL` 业务面则通过 `apisix.tail5e888.ts.net:3306` 承载爬虫采集/落库侧存储；本轮 gaokaozhiyuan 基础库 follow-up 的样本覆盖核对来自 `MySQL` 源侧现状，但业务层真源口径落在内网 `PostgreSQL` 业务面。应用层统一只经 APISIX 访问内网服务，`DEV-018` 固化了基础表到对象层的映射草案，`DEV-020` 进一步把下一会话范围收敛为字段标准化、治理字段补齐与对象层承接清单；内网 MySQL / PostgreSQL 裸库仅作维护直连对象，外网 Supabase 仅承担内网 Supabase 备份；commander 已在 `#32` 追加 follow-up note `227`，继续把该单维持为未来阶段锚点

## Canonical Status Model
- `todo`: 已登记，未开始
- `in_progress`: 已开工，有明确 owner
- `blocked`: 有阻塞，当前不能推进
- `dev_done`: 开发完成，已做最小必要验证
- `qa_done`: QA 完成，等待文档或 CE 同步
- `doc_synced`: 文档与验收材料已同步
- `ce_synced`: CE 已同步
- `done`: 正式收口完成

## Dev Owner Rule
- 只保留一张开发单，不拆两张平行 `dev-task-list`
- 一个任务卡只能有一个主 owner
- 一个文件组同一时间只能给一个 owner
- `dev-a` 与 `dev-b` 可以并行，但 `write_scope` 不允许重叠
- `dev_done` 以后必须转入 QA，不允许开发单直接写 `done`
- `dev_done` 以后对应 CE issue 必须继续保持 `opened`，等待 QA 和 Doc 在同一 issue 上续写

## Current Lanes
- `dev-a`: 输入链 / 契约 / OCR / 事件组装 / OCR runner
- `dev-b`: TWIN / GRAPH / OBS / 主链测试 / 观察层展示规则

## Task Board

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| DEV-001 | KB 结构化样例与闭环校验基线 | `dev_done` | `dev-a` | `AEdu/03_教材标准表/samples/*`, `AEdu/scripts/validate_kb_closure.py` | `validation_report.json` 为 `pass` | - | 转 QA 做正式复核 |
| DEV-002 | 冻结常量、TWIN ingest 契约、OCR 接口骨架 | `dev_done` | `dev-a` | `app/models/constants.py`, `app/models/twin_ingest_contract.py`, `app/models/ocr_interface.py` | `tests/test_twin_ingest_contract.py`, `tests/test_ocr_interface.py` | - | 冻结范围，不再扩写 |
| DEV-003 | 文本与 OCR 到标准学习事件的统一组装 | `dev_done` | `dev-a` | `app/models/event_assembler.py`, `app/models/ocr_event_bridge.py` | `tests/test_text_main_chain.py`, `tests/test_ocr_event_bridge.py`, `tests/test_ocr_integration.py` | - | 转 QA 复核路由与回归风险 |
| DEV-004 | 百度 OCR API 主路径验证与收口 | `dev_done` | `dev-a` | `app/models/ocr_interface.py`, `app/models/ocr_event_bridge.py`, `tests/test_ocr_interface.py`, `tests/test_ocr_event_bridge.py`, `tests/test_ocr_integration.py`, `scripts/ocr_8_samples.py`, `scripts/ocr_textbook.py` | 正式主路径已进一步收口：百度 provider 为唯一保留注册路径，OCR bridge / integration 证据已齐，教材图片与 PDF 脚本已切到 baidu 口径；OCR 测试本轮复核 `26/26` 通过 | - | 百度主路径证据已稳固，可继续维持 `dev_done` 口径 |
| DEV-005 | TWIN 当前态与状态更新器 | `dev_done` | `dev-b` | `app/models/twin_state.py`, `app/models/twin_updater.py` | `tests/test_text_main_chain.py` 通过 | - | 转 QA 复核状态更新正确性 |
| DEV-006 | GRAPH 写入、回滚、检索与主链判定 | `dev_done` | `dev-b` | `app/models/graph_*.py`, `app/models/retrieval_unit.py`, `app/models/main_chain_judge.py` | `tests/test_f8_rollback.py` (14/14) 与 `tests/test_f9_scenarios.py` (3/3) pytest 通过 | - | 转 QA 做联调复核 |
| DEV-007 | OBS 最小输出对象与降级展示规则 | `dev_done` | `dev-b` | `app/models/obs_models.py` | `tests/test_text_main_chain.py` 通过 OBS 段 | - | 转 QA 复核展示降级边界 |

## Next Round Intake

| task_id | title | status | owner | write_scope | evidence | blocker | next_step |
|---|---|---|---|---|---|---|---|
| DEV-008 | 家长端周报/月报解释对象收口 | `dev_done` | `dev-b` | `app/models/obs_models.py` (新增 ExplanationBlock, ActionSuggestion, FeedbackEntry, ParentMonthlyReport), `tests/test_text_main_chain.py` | 家长端 contract 相关测试已通过，已形成交付摘要 | - | 转 QA-010 做 contract 复核 |
| DEV-009 | 老师端学生详情结构化输出增强 | `dev_done` | `dev-b` | `app/models/obs_models.py` (新增 focus_subject/focus_knowledge_points/focus_exercise_types/focus_misconceptions/risk_level/recent_change/followed_up/action_items/feedback_entry/report_period, compute_focus_areas/compute_risk_level 方法), `tests/test_text_main_chain.py` | pytest 22/22 通过（含 DEV-009 专项测试），OBS-003 字段缺口已补齐 | - | 转 QA-006 做 contract 复核 |
| DEV-010 | 学校班级看板聚合与降级规则 V1 | `dev_done` | `dev-a` | `app/models/obs_models.py`, `app/models/school_dashboard.py` (新增), `tests/test_school_dashboard.py` (新增) | 班级看板模型与相关测试已通过，已形成交付摘要 | - | 转 QA-008 做结构验收 |
| DEV-011 | 接通本地 OCR runner backend 与真实失败模式 | `done` | `dev-a` | `app/models/ocr_interface.py`, `app/models/ocr_event_bridge.py`, `tests/test_ocr_integration.py` | GitLab CE `#56` 已按退役口径关闭；代码与脚本已切为 baidu-only，local runner/provider 已从代码路径退出，本项按策略变更完成生命周期收口 | - | 生命周期已收口；不再继续 backend 接通实现 |
| DEV-012 | 反馈闭环事件记录与回流接口 V1 | `dev_done` | `dev-a` | `app/models/feedback_event.py` (新增 FeedbackEvent/FeedbackOption/FeedbackRouter, 4 种 feedback_type, 4 种 route_destination), `tests/test_feedback_loop.py` | pytest 16/16 通过，OBS-010 MVP 字段与回流边界已实现 | - | 转 QA-008 做 contract 复核 |
| DEV-013 | 对比维度代码化与比较结果模型 | `dev_done` | `dev-a` | `app/models/compare_dimension.py` (CompareDimension/ComparisonResult/ComparisonRule/ComparisonWindow, 6 种 compare_type, 7 种标准维度模板), `tests/test_obs_compare_dimensions.py` | pytest 9/9 通过，OBS-007 对比维度与观察口径已代码化 | - | 转 QA-006 做 contract 复核 |
| DEV-014 | 班级看板验收支撑样例与聚合断言补强 | `dev_done` | `dev-b` | `app/models/school_dashboard.py`, `app/models/obs_models.py`, `tests/test_school_dashboard.py` | pytest 18/18 通过，DashboardAssertions 聚合断言与 DashboardTestBuilder 验收样例已实现，OBS-007 compare 口径风险说明已支持；QA-008 已完成，本项证据已写入 `#31` 生命周期评论（note 206） | - | 生命周期已同步；后续只维护阶段三主线引用一致性 |
| DEV-015 | 反馈闭环验收支撑样例与回流断言补强 | `dev_done` | `dev-a` | `app/models/feedback_event.py`, `tests/test_feedback_loop.py`, `AEdu/08_观察层与产品层/10_产品交互与反馈闭环.md`, `AEdu/08_观察层与产品层/qa_008_feedback_samples.json`, `AEdu/08_观察层与产品层/feedback_boundary_rules.md` | pytest 16/16 通过 + 12 个验收样例固化 + 8 条回流断言固化；DEV-015 交付结论：最小验收支撑已就绪；QA-008 已完成，本项证据已写入 `#31` 生命周期评论（note 206） | - | 生命周期已同步；后续只维护阶段三主线引用一致性 |
| DEV-016 | 反馈闭环可追溯指标与试点问题库骨架 | `dev_done` | `dev-a` | `app/models/feedback_event.py`, `tests/test_feedback_traceability.py` | 已补 `PilotProblem`、`FeedbackTraceabilitySnapshot`、`FeedbackTraceabilityBuilder`，把反馈处理完成率 / 问题关闭率 / 干预执行回填率与周复盘汇总能力落到代码；反馈链联合回归 `20/20` 通过，并已写入 `#31` 生命周期评论（note 206） | - | QA-011 已完成且生命周期已同步；后续只维护阶段三主线引用一致性 |
| DEV-017 | 清理返回值式测试写法并补齐标准维度查找兼容 | `qa_done` | `dev-b` | `tests/test_f8_rollback.py`, `tests/test_school_dashboard.py`, `tests/test_text_main_chain.py`, `tests/test_feedback_loop.py`, `tests/test_obs_compare_dimensions.py`, `app/models/compare_dimension.py` | 已把 5 个目标文件中被 pytest 收集到且返回非 `None` 的顶层 `test_*` 全部改成 pytest 合规形态；同时补齐 `get_standard_dimension()` 对模板键与 `dimension_id` 的兼容查找；5 文件专项复跑 `79/79` 通过，关键基线 `112/112` 通过且 `0 warnings`，扩展兼容口径 `125/125` 通过且 `0 warnings` | - | QA-013 已完成；后续只维护 warning 清零后的本地真源一致性 |
| DEV-018 | gaokaozhiyuan 基础表到志愿对象层映射草案 | `qa_done` | `dev-a` | `APISIX apisix.tail5e888.ts.net:3306 -> MySQL gaokao.china_*`, `AEdu/09_推演与决策层/10_志愿填报推演框架.md`, `AEdu/10_规则与外部数据/01_地区规则接入标准.md`, `AEdu/10_规则与外部数据/02_高考历史数据接入规范.md`, `AEdu/10_规则与外部数据/03_政策更新与版本管理.md`, `AEdu/10_规则与外部数据/04_外部数据质量校验规则.md`, `AEdu/11_系统架构与工程实现/07_数据存储与索引设计.md` | 已完成 gaokaozhiyuan 基础层映射草案：`APISIX` 当前承载 `MySQL` 与 `PostgreSQL` 两类业务面，其中 `PostgreSQL` 业务面通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 承载业务主库、向量数据库以及从 `MySQL` 汇入后的基础数据，而 `MySQL` 业务面通过 `apisix.tail5e888.ts.net:3306` 承载爬虫采集/落库侧存储；本项对基础表样本覆盖的现场核对来自 `MySQL` 源侧现状，业务层最终口径落在 `PostgreSQL` 业务面；内网 MySQL / PostgreSQL 裸库仅作维护，不作应用直连；外网 Supabase 仅承担内网 Supabase 备份；后续需统一 `province(_source) / year / batch_name / school_uuid / major_*` 到 `region_id / exam_year / batch_code / school_id / major_id`，并为规则版本、数据校验、方案/推演对象层保留承接位置；本轮不改业务代码、不改数据库结构 | - | 等待后续规则层 / 方案层 / 推演结果层正式立项，再决定是否从基础层标准化进入对象层实现 |
| DEV-019 | cmux 正式运行面全流程启动链验证 | `dev_done` | `dev-a` | `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`, `/Users/busiji/.agents/skills/cmux/scripts/regress_bootstrap_claude_runtime.py`, `workspace/artifacts/cmux-runtime/cmux-assignment.json` | 交付结论: runtime 契约一致，无会话内临时身份注入痕迹；4-pane 拓扑、bot 顺序与 live refs 均符合 | - | 转 QA 做正式复核 |
| DEV-020 | gaokaozhiyuan 基础层字段标准化后续项拆分 | `dev_done` | `dev-a` | `workspace/projects/AEdu/dev-task-list.md`, `workspace/projects/AEdu/qa-task-list.md`, `workspace/projects/AEdu/doc-task-list.md`, `workspace/projects/AEdu/rea-task-list.md`, `workspace/projects/AEdu/ce-sync-plan.md` | 已在只读分析中把 follow-up 范围收敛为字段标准化与对象层承接清单：应用层统一只经 APISIX 访问内网服务；其中本轮被核对的是 `apisix.tail5e888.ts.net:3306` 暴露的 MySQL `gaokao`.`china_*` 源侧现状，而业务层真源仍落在通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 暴露的 `PostgreSQL` 业务面；内网 MySQL / PostgreSQL 仅作维护，外网 Supabase 仅承担内网 Supabase 备份；当前 7 张 `china_*` 表继续作为测试阶段基础数据库；后续只允许统一 `province(_source) / year / batch_name / school_uuid / major_*` 到 `region_id / exam_year / batch_code / school_id / major_id`，并为规则版本、数据校验、方案/推演结果层保留承接位置；本轮不改代码、不改数据库、不改文档 | `3` 张 admission / province score 表仍为空；正式推演前仍需补齐真实样本、年份 / 地区分布说明与治理对象 | `#32` 保持 `opened`；后续仅允许继续字段标准化 / 治理字段 packet，不启动阶段四实现 |

## Update Rule
- 新任务先登记为 `todo`
- owner 接手后改为 `in_progress`
- 遇到外部依赖、资料前提或环境问题时改为 `blocked`
- 有代码证据和最小验证后改为 `dev_done`
- 后续 `qa_done`、`doc_synced`、`ce_synced` 由其他单据推动，不在本单主动宣告
- 开发完成后只允许写“转 QA”，不允许写“CE 可关闭”

## Evidence Rule
- `evidence` 只写真实文件、测试或脚本结果
- 不把口头判断写成完成证据
- 同一任务若存在残余风险，写进 `blocker` 或 `next_step`
