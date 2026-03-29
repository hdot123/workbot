# AEdu Dev Task List

## Status
- `completed`
- 首轮结构化样例与闭环校验完成时间：2026-03-24
- 文本主链实现与最小运行验证完成时间：2026-03-26
- F9 检索装配与主链判定完成时间：2026-03-26
- 当前结果：`F1-F11` 全部完成，最小 E2E 测试通过，F9 3/3 场景通过，主链判定 pass

## Scope
- 只做 AEdu 第一阶段最小闭环研发任务
- 冻结范围：安徽 / 高中 / 高一 / 物理 / `PHY_PEP_G1_V1`
- 当前执行输入源：家长文本、老师反馈文本
- 单页 OCR 与剩余 PDF 册次深化处理暂缓，等待资料前提与资源条件
- 不扩到 `SIM` / 大规模 `GRAPH` / 多地区 / 多学科 / 多版本
- 未经明确允许，不要 `commit`

## Task Count
- 已完成任务数：`31`
- 当前待执行任务数：`3` (F9 检索装配相关，等待资源)
- 当前文件按任务卡粒度展开

## Task Cards
1. `F1-T1` 定义章节树节点模型。状态：`completed`
2. `F1-T2` 实现冻结口径校验。状态：`completed`
3. `F1-T3` 录入首版章节树样例。状态：`completed`
4. `F2-T1` 定义知识点对象模型。状态：`completed`
5. `F2-T2` 定义知识点准入规则。状态：`completed`
6. `F2-T3` 产出首批知识点样例。状态：`completed`
7. `F3-T1` 定义能力点对象模型。状态：`completed`
8. `F3-T2` 定义 `knowledge -> ability` 映射规则。状态：`completed`
9. `F3-T3` 产出首批能力点样例。状态：`completed`
10. `F4-T1` 定义锚点对象模型。状态：`completed`
11. `F4-T2` 定义锚点引用关系。状态：`completed`
12. `F4-T3` 产出首批锚点样例。状态：`completed`
13. `F5-T1` 定义最小闭环校验规则。状态：`completed`
14. `F5-T2` 组装首个完整样例包。状态：`completed`
15. `F5-T3` 输出最小验收结果。状态：`completed`
16. `F5-T4` 已落冻结范围常量与门禁常量。状态：`completed`
17. `F5-T5` 已落 TWIN ingest 输入契约与校验决策模型。状态：`completed`
18. `F5-T6` 已落 OCR 输入接口层与 provider 骨架。状态：`completed`
19. `F6-T1` 文本输入到标准学习事件的统一组装。状态：`completed`
20. `F7-T1` 定义 TWIN 当前态实体模型。状态：`completed`
21. `F7-T2` 实现 TWIN 状态更新器。状态：`completed`
22. `F7-T3` 实现 TWIN 审计留痕与广播对象。状态：`completed`
23. `F8-T1` 定义 GRAPH 最小对象模型。状态：`completed`
24. `F8-T2` 实现 GRAPH 最小写入链。状态：`completed`
25. `F9-T1` 实现 Retrieval Unit 最小检索装配。状态：`completed`
26. `F9-T2` 组装文本主链联调样例。状态：`completed`
27. `F9-T3` 输出主链通过 / 阻断判定。状态：`completed`
28. `F10-T1` 定义 OBS 家长周报最小输出对象。状态：`completed`
29. `F10-T2` 定义 OBS 老师学生详情最小输出对象。状态：`completed`
30. `F10-T3` 实现 OBS 降级展示规则。状态：`completed`
31. `F11-T1` 将文本主链实现稿真实落盘到 `app/models`。状态：`completed`
32. `F11-T2` 对已落盘代码执行一次最小运行验证。状态：`completed`
33. `F11-T3` 汇总运行结果并回写主链当前结论。状态：`completed`

## Grouping
- `F1` 章节树标准化：`F1-T1` ~ `F1-T3` ✅
- `F2` 知识点标准入库：`F2-T1` ~ `F2-T3` ✅
- `F3` 能力点映射：`F3-T1` ~ `F3-T3` ✅
- `F4` 锚点/证据挂接：`F4-T1` ~ `F4-T3` ✅
- `F5` 最小闭环校验与样例包：`F5-T1` ~ `F5-T6` ✅
- `F6-F10` 文本主链实现稿与最小对象层：事件组装 / TWIN / GRAPH / OBS ✅
- `F11` 真实落盘与运行验证 ✅
- `F9` 检索装配与主链判定：`F9-T1` ~ `F9-T3` ✅

## Current Target Files
- `AEdu/03_教材标准表/samples/chapter_tree_schema.json`
- `AEdu/03_教材标准表/samples/knowledge_schema.json`
- `AEdu/03_教材标准表/samples/ability_schema.json`
- `AEdu/03_教材标准表/samples/anchor_schema.json`
- `AEdu/03_教材标准表/samples/chapter_tree_sample.json`
- `AEdu/03_教材标准表/samples/knowledge_sample.json`
- `AEdu/03_教材标准表/samples/ability_sample.json`
- `AEdu/03_教材标准表/samples/anchor_sample.json`
- `AEdu/03_教材标准表/samples/dependency_sample.json`
- `AEdu/03_教材标准表/samples/validation_report.json`
- `AEdu/03_教材标准表/samples/acceptance_conclusion.json`
- `AEdu/scripts/validate_kb_closure.py`
- `app/models/constants.py`
- `app/models/twin_ingest_contract.py`
- `app/models/ocr_interface.py`
- `app/models/event_assembler.py`
- `app/models/twin_state.py`
- `app/models/twin_updater.py`
- `app/models/graph_models.py`
- `app/models/graph_writer.py`
- `app/models/obs_models.py`

## Constraints
- 不要改无关 `.md` 文档
- 只处理与第一阶段最小闭环直接相关的实现文件
- 如发现范围冲突，先停下汇报
- 先完成昨天已产出代码的真实落盘与最小运行验证，再决定是否继续往后扩

## F11 验收结论
- 落盘文件：
  - `app/models/constants.py` (F5-T4)
  - `app/models/twin_ingest_contract.py` (F5-T5)
  - `app/models/ocr_interface.py` (F5-T6)
  - `app/models/event_assembler.py` (F6-T1)
  - `app/models/twin_state.py` (F7-T1)
  - `app/models/twin_updater.py` (F7-T2, F7-T3)
  - `app/models/graph_models.py` (F8-T1)
  - `app/models/graph_writer.py` (F8-T2)
  - `app/models/obs_models.py` (F10-T1 ~ F10-T3)
  - `app/models/retrieval_unit.py` (F9-T1)
  - `app/models/main_chain_judge.py` (F9-T3)
- 测试文件：`tests/test_text_main_chain.py` (F11), `tests/test_f9_scenarios.py` (F9-T2)
- 测试结果：
  - F11 E2E 测试：4/4 通过
  - F9-T2 场景测试：3/3 通过
  - F9-T3 主链判定：pass
- 结论：F1-F11 全部完成，文本主链最小闭环已跑通，检索装配与主链判定已完成

## F9 验收结论
- 落盘文件：
  - `app/models/retrieval_unit.py` (F9-T1) - Retrieval Unit 检索装配
  - `app/models/main_chain_judge.py` (F9-T3) - 主链通过/阻断判定
  - `tests/test_f9_scenarios.py` (F9-T2) - 联调场景测试
- 测试结果：
  - Normal 场景：PASS - 完整流程，knowledge_refs 正常更新
  - Degraded 场景：PASS - 低置信度事件正确路由到 review
  - Review Needed 场景：PASS - 显式 review 事件正确路由到 review
- 主链判定结论：pass（0 个 P0 阻断，0 个 P1 限制）
- 结论：F9 任务完成，检索装配与主链判定功能正常
