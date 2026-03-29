# AEdu QA Task List

## Status
- `pending`
- 前置条件：`dev` 产物已完成，等待 QA 执行

## Scope
- 只做 AEdu 第一阶段最小闭环 QA 任务
- 冻结范围：安徽 / 高中 / 高一 / 物理 / `PHY_PEP_G1_V1`
- 样例范围仅限第 1 章“运动的描述”
- 只核查当前最小闭环产物，不扩到 `OBS` / `SIM` / 大规模 `GRAPH` / 多地区 / 多学科 / 多版本
- 未经明确允许，不要 `commit`

## QA Goals
1. 确认研发产物是否完整
2. 确认冻结口径是否一致
3. 确认样例数据是否闭环
4. 确认校验脚本是否可复现跑通
5. 给出 `PASS / FAIL` 与 `P0 / P1 / P2` 问题结论

## Files Under QA
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

## QA Checklist
1. 文件完整性检查
- 核对所有 schema、sample、report、acceptance、script 文件是否存在

2. 冻结口径检查
- 核对所有核心文件是否统一使用 `CN_AH / 高中 / 高一 / 物理 / PHY_PEP_G1_V1`
- 核对是否只覆盖第 1 章“运动的描述”

3. Schema 合规检查
- 核对 4 个 schema 是否覆盖各自必填字段
- 核对 schema 中是否不存在越界范围字段或扩模块字段

4. 样例数据闭环检查
- 章节树节点是否完整挂接
- 知识点是否全部挂到章节树节点
- 能力点是否和知识点映射一致
- 锚点是否能回指知识点与能力点
- 依赖关系是否只引用已存在的知识点

5. 脚本复现检查
- 运行 `python3 AEdu/scripts/validate_kb_closure.py --data-dir ./AEdu/03_教材标准表/samples --verbose`
- 核对输出结果是否仍为 `PASS`
- 核对 `validation_report.json` 是否和实际运行结果一致

6. 验收结论检查
- 核对 `acceptance_conclusion.json` 是否与真实产物一致
- 核对其中的 `deliverables`、`validation_summary`、`conclusion` 是否可被当前文件集支撑

## Output Requirements
1. 给出 QA 结论：`PASS` 或 `FAIL`
2. 如有问题，必须按 `P0 / P1 / P2` 分级
3. 每个问题都要指明文件路径与原因
4. 先报问题，再给结论，不要空泛总结

## Blocking Rules
- 发现冻结口径不一致，直接记为 `P0`
- 发现样例断链、孤点、引用不存在，直接记为 `P0`
- 发现脚本不可复现或结果与报告不一致，直接记为 `P0`
- 发现范围扩张到本轮之外，至少记为 `P1`

## Constraints
- 不要新增需求
- 不要扩展章节范围
- 不要引入新模块联调
- 不要改 `.md` 文档
- 只在 QA 必需时改当前最小闭环直接相关文件
