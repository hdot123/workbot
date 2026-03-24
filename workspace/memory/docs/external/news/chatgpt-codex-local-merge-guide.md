# ChatGPT 对话：本地 Codex 合并冲突处理指南

> 来源：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
> 对话标题：仓库接管与环境检查
> 整理时间：2026-03-23
> 整理工具：chrome-devtools MCP

---

## 一、对话背景

**场景**：用户使用云端 Codex 和本地 Codex 同时开发 AEdu 项目的学生数字孪生（Twin）模块，产生合并冲突。

**核心问题**：
- 云端 Codex 生成了 TWIN ingest contract 模型和测试
- 本地 Codex 也做了类似修改
- 两端同时写入同一组文件导致冲突

**涉及文件**：
1. `app/models/constants.py`
2. `app/models/twin_ingest_contract.py`
3. `tests/test_twin_ingest_contract.py`

---

## 二、对话核心内容

### 2.1 冲突原因分析

**根本原因**：同一轮任务中，云端 Codex 和本地 Codex 都在修改同一组文件。

**冲突表现**：
```
<<<<<<< LOCAL
# 本地版本内容
=======
# 云端 Codex 版本
>>>>>>> REMOTE
```

**具体冲突点**：
1. `constants.py` - 冻结执行口径常量定义
2. `twin_ingest_contract.py` - 契约模型逻辑
3. `test_twin_ingest_contract.py` - 测试用例

---

### 2.2 合并方案

**合并原则**：
1. **保留本地已验证内容**：
   - `twin_ingest_contract.py` 中对 `event_status == "rejected"` 的上游拦截
   - `test_twin_ingest_contract.py` 中本地 pytest 导入修复（仓库根目录加入 sys.path）
   - `rejected` 负例覆盖

2. **吸收云端契约骨架**：
   - 冻结执行口径常量
   - 必填字段检查
   - `event_type` / `source_type` / `status` 合法性校验
   - `review_needed` / `degraded` 判定分支
   - 关键测试场景

**手动合并步骤**：
1. 打开冲突文件，识别 `<<<<<<<`、`=======`、`>>>>>>>` 标记
2. 逐块合并，保留两边需要内容
3. 删除冲突标记
4. 保存后运行验证

---

### 2.3 如何避免未来冲突

**核心规则**：**同一轮任务，只允许一个写入者**

**职责分工**：

| 角色 | 职责 | 禁止行为 |
|------|------|----------|
| **本地 Codex** | 读取代码、修改文件、运行测试、查看 diff、决定是否 commit | 不要扩展到未授权模块 |
| **云端 Codex** | 读代码、对照文档检查、提出问题清单、给最小修复建议、审核本地 diff | 不要改文件、不要应用结果、不要自动合并、不要 commit |

**推荐流程**：

```
阶段 A：只读分析
  → 只允许读取代码、读文档、给变更建议，不允许改文件

阶段 B：确定唯一执行端
  → 明确"这轮由本地执行"或"这轮由云端执行"

阶段 C：执行端改代码
  → 唯一执行端修改文件、跑测试

阶段 D：另一方审查
  → 非执行端审查结果，不直接改
```

**给云端的固定提示词**：
```
你现在是只读审查端，不是执行端。

规则：
1. 只能读取代码和给出检查意见
2. 不要修改任何文件
3. 不要生成可直接应用的写入结果
4. 不要 commit，不要 apply，不要 merge
5. 只检查我指定的文件范围
6. 输出只包含：
   - 当前检查摘要
   - 风险点
   - 下一步最小修改建议

当前执行端只有本地 Codex。
云端只能检查代码，不能写代码。
```

**给本地 Codex 的固定提示词**：
```
你是唯一执行端。

规则：
1. 只处理我指定的文件范围
2. 每次修改前先读取当前状态
3. 修改后必须跑测试验证
4. 提交前必须展示 diff 给我确认
5. 不要扩展到未授权模块
6. 不要自动 commit，等我明确指令
```

---

## 三、用户最终确定的规则

> **以后一个端处理就可以了，云端只能检查代码**

**具体执行口径**：

### 本地 Codex 负责：
- ✅ 读取代码
- ✅ 修改文件
- ✅ 运行测试
- ✅ 查看 diff
- ✅ 决定是否 commit

### 云端 Codex 负责：
- ✅ 读代码
- ✅ 对照文档/契约检查
- ✅ 提出问题清单
- ✅ 给最小修复建议
- ✅ 审核本地 diff 是否越界

### 云端明确禁止：
- ❌ 直接改文件
- ❌ 应用结果到本地
- ❌ 自动合并
- ❌ 自动 commit
- ❌ 扩展到未授权模块

---

## 四、验证命令

**检查冲突是否清除**：
```bash
# 查看工作树状态
git status --short --branch

# 查看只改动了 3 个文件
git diff -- app/models/constants.py app/models/twin_ingest_contract.py tests/test_twin_ingest_contract.py

# 检查冲突标记是否清除（不应有输出）
grep -n "<<<<<<" app/models/constants.py app/models/twin_ingest_contract.py tests/test_twin_ingest_contract.py
```

**验证编译通过**：
```bash
python3 -m py_compile app/models/constants.py app/models/twin_ingest_contract.py tests/test_twin_ingest_contract.py
```

**验证测试通过**：
```bash
python3 -m pytest tests/test_twin_ingest_contract.py -q
```

---

## 五、对 AEdu 项目的借鉴意义

### 5.1 多 Agent 协作原则

1. **单一写入源**：同一轮任务只允许一个 Agent 有写入权限
2. **审查与执行分离**：审查者不执行，执行者接受审查
3. **固定边界**：明确指定可修改的文件范围
4. **验证先行**：修改后必须验证，提交前必须展示 diff

### 5.2 应用到学生数字孪生系统

| 场景 | 写入端 | 审查端 |
|------|--------|--------|
| 契约模型修改 | 本地 Codex | 云端 Codex |
| 测试用例开发 | 本地 Codex | 云端 Codex + 人工 |
| 文档审查 | 人工 | 云端 Codex |
| 代码审查 | 人工 | 云端 Codex + 本地 Codex |

### 5.3 工程纪律

1. **范围冻结**：每次任务开始前明确可修改的文件列表
2. **变更可追溯**：所有修改必须有 git diff 记录
3. **验证自动化**：修改后自动运行 py_compile 和 pytest
4. **提交人工确认**：提交前必须人工审查 diff

---

## 六、关键结论

**核心教训**：多端同时写入同一组文件必然导致冲突，必须明确**唯一写入源**。

**固定规则**：
- **本地是唯一执行端**：负责实际修改、测试、提交
- **云端是只读审查端**：负责检查、建议、审核

**工程价值**：
1. 避免合并冲突
2. 提高开发效率
3. 保证代码质量
4. 降低人为错误

---

## 附录：完整对话链接

- ChatGPT 对话：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
