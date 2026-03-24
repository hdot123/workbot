# 库管 (Knowledge Base Manager) - 工程执行阶段记录

> 来源：https://chatgpt.com/c/69bfc5d1-f268-8390-864f-3baf33d62cc9
> 对话标题：库管 - 工程执行与契约模型测试
> 整理时间：2026-03-23
> 整理工具：gpt-web-to (opencli chatgpt-web)

---

## 一、工程执行阶段概述

### 1.1 阶段转换

**从文档治理阶段切换到工程执行阶段**：

- 不再补评审文档
- 不再继续做治理文档
- 优先执行"开发与测试契约的工程确认（代码化）"

### 1.2 统一执行口径

| 项目 | 值 |
|------|-----|
| 地区 | 安徽 |
| 学段 | 高中 |
| 年级 | 高一 |
| 学科 | 物理 |
| 教材版本 | PHY_PEP_G1_V1 |

### 1.3 当前主链路

```
KB+INGEST -> TWIN -> GRAPH -> OBS / SIM
```

### 1.4 当前聚焦文件

**只处理以下 3 个代码文件**：
- `app/models/constants.py`
- `app/models/twin_ingest_contract.py`
- `tests/test_twin_ingest_contract.py`

**需要对照的文档**：
- `AEdu/11_系统架构与工程实现/22_KB+INGEST-TWIN 输入契约.md`
- `AEdu/11_系统架构与工程实现/23_TWIN 最小验收矩阵.md`
- `AEdu/11_系统架构与工程实现/24_TWIN 端到端样例集.md`

---

## 二、接管要求与限制

### 2.1 接管要求

1. 先检查仓库与 git 状态
2. 先确认当前 3 个代码文件状态
3. 先确认测试环境是否可运行
4. 只输出：
   - 当前接管摘要
   - 当前阻塞点
   - 下一步最小动作

### 2.2 限制条件

- 不要改文档
- 不要扩展到其他模块
- 不要直接写 router / service
- 不要改变执行口径
- 先只处理当前契约模型与测试环境

---

## 三、测试环境配置

### 3.1 Python 环境

**使用临时隔离环境**：
- 环境路径：`/tmp/workbot_twin_contract_env_py39`
- 解释器：`/tmp/workbot_twin_contract_env_py39/bin/python3`
- Python 版本：3.9.6
- 未做全局安装

### 3.2 安装的依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| pydantic | 2.12.5 | 数据验证 |
| pytest | 8.4.2 | 测试框架 |

### 3.3 验证命令

```bash
# 1. 语法检查
python3 -m py_compile app/models/constants.py
python3 -m py_compile app/models/twin_ingest_contract.py
python3 -m py_compile tests/test_twin_ingest_contract.py

# 2. 执行测试
pytest tests/test_twin_ingest_contract.py -q
```

---

## 四、契约模型测试要点

### 4.1 测试目标

1. 验证契约模型文件在语法层面可编译
2. 验证 pytest 环境可正常执行
3. 验证契约逻辑已被测试覆盖并通过

### 4.2 测试通过标准

- `py_compile` 全部通过（3 个文件）
- `pytest` 测试结果：11 passed in 0.13s
- 使用临时隔离环境，未污染全局 Python

### 4.3 有效修复点

**`app/models/twin_ingest_contract.py`**：
- 补齐 `event_status == "rejected"` 的上游拦截

**`tests/test_twin_ingest_contract.py`**：
- 补齐本地导入路径
- 增加 rejected 负例覆盖

---

## 五、Bot 权限矩阵（工程执行阶段）

### 5.1 角色定位

| Bot | GitLab 角色 | 职责 | 代码写入 |
|-----|------------|------|---------|
| 用户 | Owner | 最终权限控制 | 是 |
| PMBot | Maintainer | 任务编排 | 否 |
| DevBot | Developer | 唯一代码写入执行端 | 是 |
| QABot | Developer | 验收 | 否 |
| DocBot | Developer | 文档同步 | 否 |

### 5.2 权限边界

**DevBot（唯一代码写入者）**：
- ✅ clone/pull/push 非保护分支
- ✅ 新建 feature/fix/chore 分支
- ✅ 开 MR
- ✅ 查看 pipeline
- ❌ 直接 push main
- ❌ 合并 MR

**PMBot（任务编排）**：
- ✅ 建/改 Issue
- ✅ 管 Label
- ✅ 拖 Board
- ✅ 建/改 Milestone
- ✅ 查看 MR/CI
- ✅ 必要时合并 MR
- ❌ 不直接改代码
- ❌ 不新建开发分支做实现

**QABot（验收）**：
- ✅ 读取仓库
- ✅ 查看 MR
- ✅ 查看 CI
- ✅ 写评论
- ✅ 回填验收结果
- ❌ 改代码
- ❌ 建分支推代码
- ❌ 合并 MR

**DocBot（文档同步）**：
- ✅ 读取仓库
- ✅ 查看 Issue/MR
- ✅ 写文档同步评论
- ✅ 写 Wiki/docs
- ❌ 改业务代码
- ❌ 合并 MR
- ❌ 改任务范围

### 5.3 必须配置的系统限制

**main 分支保护**：
- Allowed to push: No one
- Allowed to merge: Maintainers
- CI 通过才能合并：必开
- 有冲突不能合并：必开
- 不允许绕过 MR：必开

---

## 六、阻塞点与解决方案

### 6.1 常见阻塞点

1. **仓库未接入执行环境**
   - 表现：容器内没有仓库工作树，无法执行 git status
   - 解决：上传目标文件或提供 GitHub 仓库路径

2. **合并冲突**
   - 表现：云端 Codex 的改动与本地改动冲突
   - 解决：只手动合并冲突文件，不扩大范围

3. **权限不足**
   - 表现：无法推送到保护分支
   - 解决：按权限矩阵配置 Bot 角色

### 6.2 解决方案原则

**最小动作原则**：
- 只处理当前限定范围内的文件
- 不要直接全量覆盖本地版本
- 不要把冲突扩大到其他模块
- 不要顺手去改 router / service / 文档

---

## 七、工程执行检查清单

### 7.1 环境准备

- [ ] Python 虚拟环境已创建
- [ ] pytest 已安装
- [ ] pydantic 已安装
- [ ] 项目代码可访问

### 7.2 代码验证

- [ ] `py_compile` 通过
- [ ] `pytest` 通过
- [ ] 测试结果 ≥ 10 passed

### 7.3 Git 配置

- [ ] 仓库已 clone
- [ ] 分支保护已配置
- [ ] Bot 权限已设置
- [ ] MR 流程可正常运作

---

## 八、下一步动作

1. 确认仓库接入当前会话环境
2. 读取并对照契约文档
3. 检查当前 3 个代码文件状态
4. 跑 pytest 验证
5. 在限定范围内处理契约模型与测试环境

---

**维护人**：项目负责人
**版本**：V1.0
**最后更新**：2026-03-23
