# AEdu CE Sync Plan

## Purpose
- 本文件只规划 GitLab CE 的正式任务状态同步
- CE 只表达正式任务状态，不表达 bot 内部分工
- 一张 CE 正式任务单必须贯穿 `dev -> qa -> doc -> ce -> done` 全生命周期
- 除非任务真正到达 `done`，否则 CE issue 不关闭

## Canonical Status Mapping
- 本地 `todo` / `in_progress`: CE 保持 `opened`，必要时补进展评论
- 本地 `blocked`: CE 保持 `opened`，补阻塞评论与解除条件
- 本地 `dev_done`: CE 保持 `opened`，评论"开发完成，待 QA"
- 本地 `qa_done`: CE 保持 `opened`，评论"QA 完成，待文档同步"
- 本地 `doc_synced`: CE 更新描述或评论，准备正式收口
- 本地 `ce_synced`: CE 已完成本轮同步动作
- 本地 `done`: 对应 issue 满足条件后关闭

## CE Update Rule
- 不给 `dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 单独建正式任务
- 优先更新已有 issue，不新造平行编号体系
- 先同步阶段单和主线单，再同步子任务单
- comment 先于 close；没有证据不关单
- `dev_done` 不是 close 条件，`qa_done` 也不是 close 条件
- QA、Doc、Commander 后续进度必须继续写回同一张 CE issue，不新开替代单
- 只有当开发、QA、文档同步、CE 同步都完成后，才允许从 `opened` 进入关闭

## Lifecycle Rule
- 一个正式任务只允许一个 CE issue 承接全生命周期
- `dev` 只负责把任务推进到 `dev_done`
- `qa` 在同一 issue 上继续补 `qa_done` 或 `blocked`
- `doc` 在同一 issue 上继续补 `doc_synced`
- `commander` 在同一 issue 上执行最终 `ce_synced` / `done`
- 不允许因为开发完成就关闭 issue，再让 QA 或 Doc 无处续写进度

## Current Issue Groups

| issue group | current plan | target action |
|---|---|---|
| `#28` 总表 | 已评论 | 保持 `opened`，继续承接阶段三 / 阶段四推进 |
| `#29` 阶段一主线 | 已评论 | 保持 `opened`，作为历史阶段锚点保留，不再承接新一轮执行 |
| `#30` 阶段二主线 | 已评论 | 保持 `opened`，记录 OCR 正式主路径已 baidu-only 收口 |
| `#31` 阶段三主线 | 已评论 | 保持 `opened`，承接阶段三生命周期守护与后续新一轮任务 |
| `#32` 阶段四主线 | 已评论 | 保持 `opened`，作为未来阶段锚点保留；当前仅有准入文档与设计支撑，未进入真实实现前不启动 |
| `#33` KB+INGEST 主线 | 已评论 | 保持 `opened`，明确 OCR 正式主路径已完成收口 |
| `#34-36` 阶段二子主线 | 已补证据 | 已评论并关单 |
| `#37-55` 已完成子任务 | 证据已齐 | 已评论并关单 |
| `#56` F6-T2 | 已退役关单 | 已评论并关闭，作为本地 OCR runner 退役/收口处置归档 |
| `#57-69` 已完成子任务 | 证据已齐 | 已评论并关单 |

## Suggested Execution Order

1. ~~先同步本地文档与验收文件~~（已完成）
2. ~~更新 `#28` 与 `#30`~~（已完成）
3. ~~更新 `#31` 与 `#33`~~（已完成）
4. ~~批量更新 `#34-69`~~（已完成；`#56` 除外）
5. ~~关单检查：`#51`~~（已完成）
6. ~~OBS Contract 冻结（5 文档）~~（已完成，状态：可评审）
7. ~~OPS 同步（4 文档）~~（已完成，状态：可评审）
8. ~~启动 6+1 评审（OBS 5 文档 + OPS 4 文档）~~（已完成）
9. ~~评审通过后启动 DEV-008/009/010/012~~（已完成）
10. ~~`#56` 按退役口径补评论并关单；不影响百度 OCR 主路径口径~~（已完成）

## Execution Result (2026-04-02)

- 保持 `opened`：`#28`、`#29`、`#30`、`#31`、`#32`、`#33`
- 已评论并关闭：`#34-36`、`#37-55`、`#56`、`#57-69`
- `#51` 已按验收材料与 validation 证据完成关单
- **阶段锚点说明**：
  - `#29`：阶段一骨架建立期已成为历史阶段锚点；当前代码、文档与 task-list 均已越过阶段一执行态，不再向该单派发新一轮实现
  - `#32`：阶段四推演层建设期仍未进入真实实现；当前已具备 `SIM-001~007/012`、`ARCH-032/033/034`、`OPS-013` 与 `NAV-009` 等准入支撑，但本地仓库仍缺独立 SIM/风险预测/影子推演实现文件、测试入口与端到端跑通记录，因此只保留未来阶段锚点，待阶段三观察层站稳后再评估是否进入
- **OCR 生命周期说明**：
  - `#56`：已按退役口径评论并关闭；本地 runner/provider 已从代码与脚本路径退出
  - `#31` 与 `#56` 已完成分离：阶段三主线任务（DEV-008/009/010/012）不依赖 `#56`
  - OCR 正式方案固定为 `百度 OCR API only`
- **QA-008 完成说明**：
  - 班级看板聚合与反馈闭环回归通过 (34/34 pytest 通过)
  - 阶段三主线 QA 完成度：QA-006/007/008/010 已完成，QA-009 已随 `#56` 退役关单完成生命周期收口

## Phase 3 Intake (2026-04-02)

### OBS Contract 冻结状态

| 文档 | 状态 | CE 映射 | 评审结论 |
|------|------|--------|----------|
| OBS-002 家长端展示规则 | 已冻结 | #31 | 6+1 评审通过 |
| OBS-003 老师端展示规则 | 已冻结 | #31 | 6+1 评审通过 |
| OBS-008 家长周报月报设计 | 已冻结 | #31 | 6+1 评审通过 |
| OBS-009 学校班级看板设计 | 已冻结 | #31 | 6+1 评审通过 |
| OBS-010 产品交互与反馈闭环 | 已冻结 | #31 | 6+1 评审通过 |

### OPS 同步状态

| 文档 | 状态 | 依赖的 OBS | CE 映射 | 评审结论 |
|------|------|-----------|--------|----------|
| OPS-005 家长使用引导 | 已冻结 | OBS-002/008 | #31 | 6+1 评审通过 |
| OPS-004 老师培训与操作手册 | 已冻结 | OBS-003 | #31 | 6+1 评审通过 |
| OPS-007 运营指标与复盘机制 | 已冻结 | OBS-010 | #31 | 6+1 评审通过 |
| OPS-002 试点学校实施方案 | 已冻结 | OBS-002/003/009 | #31 | 6+1 评审通过 |

### 阶段三任务入口

| task_id | title | status | CE 映射 | 依赖 | 当前状态 |
|---------|-------|--------|--------|------|----------|
| DEV-008 | 家长端周报/月报解释对象收口 | dev_done | #31 | OBS-002/008 冻结 | **QA-010 已完成**；后续由 commander 统一维护 `#31` 生命周期 |
| DEV-009 | 老师端学生详情结构化输出增强 | dev_done | #31 | OBS-003 冻结 | **QA-006 已完成**；后续由 commander 统一维护 `#31` 生命周期 |
| DEV-010 | 学校班级看板聚合与降级规则 V1 | dev_done | #31 | OBS-009 冻结 | **QA-008 已完成**；后续由 commander 统一维护 `#31` 生命周期 |
| DEV-011 | 接通本地 OCR runner backend | done | #56 | 已完成退役关单 | **生命周期已收口**：代码与脚本已切 baidu-only，本项按策略变更完成退役收口 |
| DEV-012 | 反馈闭环事件记录与回流接口 V1 | dev_done | #31 | OBS-010 冻结 | **QA-008 已完成** (34/34 pytest 通过)；后续由 commander 统一维护 `#31` 生命周期 |
| DEV-013 | 对比维度代码化与比较结果模型 | dev_done | #31 | QA-006 已完成 | **已完成**，原 QA-006 阻塞已解除 |

### REA-008 审计结论

- `AEdu/12_实施与试点运营/02_试点学校实施方案.md`、`04_老师培训与操作手册.md`、`05_家长使用引导.md` 与 `OBS-002/003/009/010` 的真实实现边界一致，可支撑当前试点实施与培训口径。
- 真实证据链为 `tests/test_text_main_chain.py`、`tests/test_school_dashboard.py`、`tests/test_feedback_loop.py`；本轮联合复跑 `56/56` 通过。
- 已纠正本地 `qa-task-list.md` 中 `QA-006/007` 旧的不存在测试文件引用，避免继续以假路径承接 CE 生命周期。

### REA-006 审计结论

- `OBS-010`、`OPS-006`、`OPS-007`、`OPS-008` 要求的“反馈可追踪、问题可关闭、复盘可汇总”此前只落实到 `FeedbackEvent` 的记录/路由层，本轮已补齐到代码。
- 当前真实实现新增 `PilotProblem`、`FeedbackTraceabilitySnapshot`、`FeedbackTraceabilityBuilder`，可承接最小问题库、反馈处理完成率、问题关闭率、干预执行回填率和周复盘汇总能力。
- 真实证据链为 `app/models/feedback_event.py`、`tests/test_feedback_loop.py`、`tests/test_feedback_traceability.py`；本轮联合回归 `20/20` 通过。

### REA-005 审计结论

- 已确认阶段三当前真实实现仍位于观察层增强期边界：覆盖家长周报/月报、老师端详情、班级/学校看板、对比维度、反馈闭环与最小问题库/复盘口径。
- 未发现阶段四干预动作库、InterventionSimulator、风险预测模型、志愿填报推演等真实实现落地；当前仓库中相关能力仍停留在战略/设计文档层，不构成越阶段开发。
- 已修正 `STR-008` 中“进入阶段三启动准备”与“`#56` 仍 opened”旧口径，使阶段判断文档与当前代码、task-list、CE 事实一致。

**#31 与 #56 关系说明**：
- `#31` 承载阶段三观察层增强期主线任务（DEV-008/009/010/012）
- `#56` 独立承载 OCR runner 退役/收口处置（DEV-011），现已关闭
- 阶段三主线不依赖 `#56`，可独立推进至完成
- `#56` 已按退役口径关单，不再作为 lifecycle 阻塞项
- OCR 正式主路径固定为 `百度 OCR API only`；本地 runner 已退出代码与脚本路径

## Close Preconditions
- 对应实现文件已经存在
- 至少有一条最小验证证据
- QA 已形成正式结论，且没有未消除的阻断
- 文档与验收材料已同步到当前事实
- CE 同一 issue 上已经补齐 `dev_done -> qa_done -> doc_synced -> ce_synced` 的生命周期记录

## Retirement Close Rule
- 当 issue 对应方案已被正式替代，且不再作为当前实现目标时，可按“退役关单”而不是“实现完成关单”处理
- 退役关单前提：
  - 替代方案已明确且已落地到代码 / 脚本 / 本地 task-list
  - 原方案为何不再继续推进已在同一 CE issue 上写清楚
  - 当前 issue 标题/描述已改到真实定位，避免继续误导执行
  - 关联阶段单已同步说明该 issue 不再阻挡正式主路径
- 退役关单动作：
  - 先补一条“退役关单”评论，明确替代方案、已完成证据、以及关单原因
  - 再把 issue 从 `opened` 改为关闭

## 反馈闭环验收口径 (DOC-012)

### 反馈类型与分流映射

| feedback_type | 来源角色 | 去向 (route_destination) | 处理池 | 影响范围 |
|---------------|----------|--------------------------|--------|----------|
| `state_calibration` | 家长/老师 | `review_queue` | 状态校准池 | 可能影响 StudentTwinAgent/图谱/报告口径 |
| `product_experience` | 全部角色 | `product_pool` | 产品优化池 | 主要影响 UI/交互/文案 |
| `implementation_progress` | 学校/运营 | `ops_pool` | 运营动作池 | 影响试点推进节奏和实施策略 |
| `exception_report` | 全部角色 | `tech_pool` | 技术问题池 | 高优先级修复链，影响系统稳定性 |

### MVP 验收边界

**DEV-012 已实现范围**：
- `FeedbackEvent` 对象：4 种 `feedback_type` 枚举
- `FeedbackRouter`：4 种 `route_destination` 自动分流
- 反馈对象字段：`feedback_id`, `source_role`, `source_user_id`, `tenant_id`, `target_type`, `target_ref`, `feedback_type`, `feedback_text`, `created_at`, `status`, `routed_to`

**QA-008 验收结论**：
- 班级看板聚合规则与反馈闭环分流回归通过 (34/34 pytest 通过)
- 4 种 feedback_type 分流正确，审计边界已验证
- 生命周期已由 commander 维护到 `#31`，当前转入阶段三主线守护

### 审计边界

| 审计项 | 口径 | 证据位置 | QA-008 结论 |
|--------|------|----------|------------|
| 反馈提交成功率 | 成功提交数/反馈尝试数 | `tests/test_feedback_loop.py` | PASS |
| 分流正确率 | 正确路由数/总分流数 | `tests/test_feedback_loop.py` | PASS (100%) |
| 处理状态可追踪 | 有 `status` + `routed_to` 字段 | `app/models/feedback_event.py` | PASS |
| 闭环可见性 | 用户侧"已收到/已处理"状态 | 待产品层实现前端展示 | 后端就绪 |

## CE Comment Templates

### 阶段单评论模板

**#31 阶段三主线**（QA-006/007/008/010 完成后）：
```
【2026-04-02 同步】阶段三观察层增强期 QA 同步已执行。
- QA-006（三端 contract）：已完成，阻塞项已通过 DEV-009/013 解除
- QA-007（周报/月报与学生详情 E2E）：已完成，周报/月报与学生详情最小串联链路通过
- QA-008（班级看板 + 反馈闭环）：已完成，34/34 pytest 通过，4 种 feedback_type 分流验证通过
- QA-010（家长端 contract）：已完成，9/9 项 pass
- OCR 正式主路径：百度 OCR API only，代码与脚本已切 baidu-only，OCR 相关测试本轮复核 26/26 通过
- #56：已转为本地 runner 退役/收口处置项，不影响阶段三主线，也不代表百度 OCR 主路径未通过
- 下一步：DOC 准备 doc_synced，commander 在 #31 执行 CE 同步评论
```

**#28 总表**：
```
【2026-04-02 同步】阶段二正式 CE 同步已执行。
- KB 闭环校验：PASS（validation_report.json / VAL_KB_20260402_050912）
- OCR 正式主路径：百度 OCR API only，mock / bridge / integration 证据已齐
- 主链回归测试：25/25 pytest 通过
- 本地 task-list 生命周期已对齐：dev_done -> qa_done -> doc_synced -> ce_synced
```

**#30 阶段二主线**：
```
【2026-04-02 同步】阶段二主链 CE 同步已执行。
- DEV：7/7 dev_done
- QA：5/5 qa_done
- DOC：8/8 doc_synced，现已补 commander ce_synced
- OCR 正式主路径：百度 OCR API only，代码与脚本已切 baidu-only，OCR 相关测试本轮复核 26/26 通过
- #56：转为本地 runner 退役/收口处置项，不代表百度 OCR 主路径阻塞
```

**#31 阶段三主线**（历史模板，已执行）：
```
【2026-04-02 同步】阶段三观察层增强期文档同步已启动。
- OBS Contract：5 文档已冻结为"可评审"
- OPS 同步：4 文档已冻结为"可评审"
- 下一步：启动 6+1 评审，评审通过后启动 DEV-008/009/010/012
```

### 关单评论模板 (#51)
```
【2026-04-02 关单】验收文件已同步，满足关单条件。
- validation_report.json：VAL_KB_20260402_050912（PASS）
- acceptance_conclusion.json：已对齐 2026-04-02 事实
```

## Auto Finish Log

- `commander_lifecycle_sync`: `2026-04-02` 已在 `#31` 追加生命周期评论，确认 DEV-014/015 证据复核完成、QA-008 `34/34` pytest 通过、`#56` 已转入独立退役闭环并完成关闭。
- `commander_lifecycle_sync_round2`: `2026-04-02` 已在 `#31` 追加 note `206`，补齐 DEV-014/015/016、QA-010/011、DOC-012/013 与 REA-005/006/008 的阶段三生命周期记录，并明确当前只余 `REA-002` 外部前提跟踪。
- `total_board_sync`: `2026-04-02` 已在 `#28` 追加 note `207`，更新总表到“阶段二收口、阶段三观察层增强期推进中、`#56` 已关闭、阶段四尚未进入真实实现”的当前事实。
- `baidu_real_api_smoke_verified`: `2026-04-02` 已使用系统环境变量中的百度 OCR 凭据执行真实 API smoke；样例图 `AEdu/13_原始资料库/OCR/高中物理/样本截图/01_封面.png` 返回 `event_status=success`、`review_needed=false`、`overall_confidence=0.9826`，并已把 `ocr_qa_evidence.json`、`QA-004`、`REA-002` 与验收结论回写到最新事实。
- `ocr_canonical_sync`: `2026-04-02` 已按 pane 复核结论回写本地口径：正式 OCR 主路径固定为百度 OCR API only，`QA-004` 维持 `qa_done`，`#56 / DEV-011 / QA-009` 仅保留为本地 runner 独立残余验证。
- `baidu_runtime_cutover`: `2026-04-02` 已完成 baidu-only 代码收口：`ocr_interface.py` 去除 local provider 入口，教材图片/PDF 脚本切到 baidu，OCR 测试复核 `26/26` 通过；`#56` 转为待 commander 退役/收口处置项。
- `ocr_issue56_reframe`: `2026-04-02` 已通过 GitLab CE API 改写 `#56` 标题/描述为“本地 OCR runner 退役/收口处置”；当前仅剩退役关单规则动作待处理。
- `ocr_issue56_retired_close`: `2026-04-02` 已补退役关单评论并关闭 `#56`；`DEV-011 / QA-009 / REA-007` 按策略变更完成生命周期收口。
- `rea_008_trial_material_audit`: `2026-04-02` 已完成试点实施材料与观察层价值口径审计；确认 OPS 试点/培训/家长引导文档与 OBS-002/003/009/010 的真实实现边界一致，并纠正 `QA-006/007` 的旧测试文件引用到真实证据链。
- `rea_006_feedback_traceability`: `2026-04-02` 已完成反馈闭环与运营指标可追溯性审计；新增 `PilotProblem`、`FeedbackTraceabilitySnapshot`、`FeedbackTraceabilityBuilder` 与 `tests/test_feedback_traceability.py`，把最小问题库与反馈追溯指标口径落到代码并通过 `20/20` 联合回归。
- `rea_005_phase3_admission_audit`: `2026-04-02` 已完成阶段三观察层准入真实性审计；确认当前真实实现未越入阶段四推演层，并已修正 STR-008 中阶段判断与 `#56` 生命周期的旧口径。
- `phase_anchor_guard_sync`: `2026-04-02` 已确认 `#29` 与 `#32` 仍为 `opened` 阶段锚点，并已通过 GitLab CE API 追加 `#29 note 212`、`#32 note 213` 说明历史/未来阶段语义；同时把本地 `ce-sync-plan` 与四张 task-list 的 Overall Status 回写为“无活跃执行卡、转入阶段生命周期守护”的当前事实。
- `rea_009_phase4_gate_audit`: `2026-04-02` 已完成 `#32` 阶段四准入条件审计，并通过 GitLab CE API 追加 `#32 note 214`；结论是 SIM 准入文档齐备但本地仓库仍无独立阶段四实现文件、测试入口与端到端跑通记录，`#32` 继续仅作为未来阶段锚点保留。
- `rea_010_repo_ce_landing_audit`: `2026-04-02` 已由 `rea-bot` 完成全代码与 CE opened 落点总审查；结论是四张 task-list 与代码/测试现场一致，`#29/#32` 仅作阶段锚点，`#28/#30/#31/#33` 继续承接生命周期或历史追溯；commander 随后已通过 GitLab CE API 刷新 `#28/#29/#30/#31/#32/#33` description 到最新事实，并在 `#28` 追加 audit note `223` 留痕。
- `pytest_env_restore_and_rerun`: `2026-04-02` 已在项目 `.venv` 补装 `pytest`，并现场复跑关键测试集（OCR / 主链 / 看板 / 反馈闭环 / 可追溯 / 对比维度 / F8 / F9），结果 `112 passed, 44 warnings`；当前新增的真实残余是若干老测试仍保留 tuple return 写法，触发 `PytestReturnNotNoneWarning`。
- `commander_auto_finish_correction`: `2026-04-02` 已在 `#31` 追加 note `216`，更正自动收尾评论口径：`REA-009` 结论有效，但自动评论不再作为正式生命周期结论；`#56` 已关闭，后续 CE 生命周期同步由 commander 复核维护。
- `warning_residual_noncode_session`: `2026-04-02` 已执行 REA-011 / QA-012 / DOC-014 非代码会话；结论是关键基线仍为 `112 passed, 44 warnings`，若额外纳入 `tests/test_twin_ingest_contract.py` 这 `13` 个兼容契约测试，则扩展口径为 `125 passed, 44 warnings`；warning 类型全部为 `PytestReturnNotNoneWarning`，根因锁定为 5 个测试文件中 `44` 个顶层 `test_*` 函数显式 `return tuple` 的旧写法；当前按“测试形态残余、非功能失败、低于主线路径的技术债”口径维护，本轮未开新的开发卡，也不新增 CE 生命周期评论。
- `warning_cleanup_code_session`: `2026-04-02` 已完成 REA-012 / DEV-017 / QA-013 / DOC-015 warning 清理代码会话；5 个目标文件中被 pytest 收集到且返回非 `None` 的顶层 `test_*` 已全部转为 pytest 合规形态，`compare_dimension.get_standard_dimension()` 也已补齐模板键与 `dimension_id` 的兼容查找；专项复跑 `79 passed, 0 warnings`，关键基线复跑 `112 passed, 0 warnings`，若额外纳入 `tests/test_twin_ingest_contract.py`，扩展兼容口径为 `125 passed, 0 warnings`；本轮不涉及阶段生命周期变化，不新增 CE 生命周期评论。
- `gaokaozhiyuan_foundation_intake`: `2026-04-04` 已完成 DEV-018 / REA-013 / QA-014 / DOC-016 本地 intake 会话；结论是内网环境优先于本机环境，本机数据库实例只作备份/应急使用。`APISIX` 当前承载 `MySQL` 与 `PostgreSQL` 两类业务面，其中 `PostgreSQL` 业务面通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 承载业务主库、向量数据库以及从 `MySQL` 汇入后的基础数据，`MySQL` 业务面则通过 `apisix.tail5e888.ts.net:3306` 承载爬虫采集/落库侧存储，而本轮 intake 只核对了 `MySQL` 源侧现状：应用层统一只经 APISIX 访问内网服务，当前 APISIX `apisix.tail5e888.ts.net:3306` 暴露的 MySQL `gaokao`.`china_*` 反映的是基础数据源侧状态，不等于完整志愿推演层最终真源；内网 MySQL / PostgreSQL 裸库仅作维护，不作应用直连，外网 Supabase 仅承担内网 Supabase 备份；`china_universities_base`、`china_majors_dictionary`、`china_enrollment_plans`、`china_university_admission_scores`、`china_major_admission_scores`、`china_gaokao_score_rankings`、`china_gaokao_province_scores` 继续保留为基础数据源侧，后续仅做 `region_id / exam_year / batch_code / school_id / major_id` 等字段标准化与治理字段补齐；当前覆盖度为 `4/7` 表有样本、`3/7` 表为空，测试阶段 QA 结论为 `Conditional Pass`；commander 随后已通过 GitLab CE API 在 `#32` 追加基础库收口 note `225`，明确该结果仍不构成阶段四真实实现启动。
- `cmux_auto_finish`: 2026-04-06 01:46:40 已完成本轮本地收口； DEV-019->dev_done；QA-015->qa_done；DOC-017->doc_synced；REA-014->done；本地 task-list / ce-sync-plan 已回写；CE 正式生命周期同步仍由 commander 复核执行。
- `cmux_ce_sync`: 2026-04-06 已由 commander 在 `#31` 追加正式生命周期评论（note `226`）；当前阶段三主线继续保持 `opened`，后续如有下一会话真实任务仍在 `#31` 续写。
- `gaokaozhiyuan_followup_packet`: `2026-04-06` 已完成 DEV-020 / QA-016 / DOC-018 / REA-015 真实 follow-up 会话；结论是 `APISIX` 当前承载 `MySQL` 与 `PostgreSQL` 两类业务面，其中 `PostgreSQL` 业务面通过 `http://apisix.tail5e888.ts.net:9080/supabase/...` 与 `apisix.tail5e888.ts.net:5432` 承载业务主库、向量数据库以及从 `MySQL` 汇入后的基础数据，`MySQL` 业务面则通过 `apisix.tail5e888.ts.net:3306` 承载爬虫采集/落库侧存储，而本轮 follow-up 只涉及 `MySQL` 源侧现状与对象层承接边界：应用层统一只暴露 APISIX，`china_*` 在 MySQL 中继续作为基础数据源侧保留，不应被误写成最终业务真源；内网 MySQL / PostgreSQL 裸库仅作维护，不作应用直连，外网 Supabase 仅承担内网 Supabase 备份；下一会话只允许继续字段标准化、治理字段补齐与对象层承接边界整理，不进入阶段四真实实现。
- `cmux_ce_sync_issue32_followup`: `2026-04-06` 已由 commander 在 `#32` 追加 follow-up 生命周期评论（note `227`）；当前 `#32` 继续保持 `opened`，仅作为未来阶段锚点保留，正式推演前仍需补 admission / province score 数据、样本分布说明、字段标准化与规则层对接。
