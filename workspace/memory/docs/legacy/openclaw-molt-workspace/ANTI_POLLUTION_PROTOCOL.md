# 🛡️ ANTI_POLLUTION_PROTOCOL: 防污染与安全标准协议

> **级别**: HIGHEST (最高防御级)
> **状态**: ACTIVE (实时生效)
> **职责**: 防止上下文污染、数据污染、安全泄露

---

## 1. 上下文防污染 (Context Hygiene)

**目标**: 防止 AI 读取垃圾文件产生幻觉，确保认知清澈。

### 🚫 禁区 (No-Go Zones - 绝对不读)

| 目录/文件 | 原因 |
|-----------|------|
| `node_modules/` | 包含数万个依赖文件，绝对禁止读取，不仅浪费 Token 还会导致逻辑混乱 |
| `dist/`, `build/`, `.next/` | 编译产物，无需关注 |
| `.DS_Store` | 系统垃圾文件，直接忽略 |
| `archive/` | 归档目录下的历史文件，除非有明确指令，否则严禁作为参考 |
| `*.log` | 运行时日志仅供排错，不作为逻辑依据 |
| `package-lock.json` / `yarn.lock` | 除非为了解决依赖冲突，否则禁止读取 |

### ✅ 真理源 (Source of Truth - 唯一信源)

* 任何逻辑冲突，以 **`workspace/CLEAN_LOGIC.md`** 为唯一标准。
* 旧的 `.qmd` / `.txt` 笔记若与 `CLEAN_LOGIC.md` 冲突，视为"已污染数据"，直接丢弃。

---

## 2. 数据防污染 (Data Hygiene)

**目标**: 防止脏数据进入 Supabase 数据库。

### ETL 净化规则

| 规则 | 说明 |
|------|------|
| **类型强制** | 写入前必须校验数据类型（例如：分数必须是数字，且 `0 <= score <= 750`） |
| **空值清洗** | `null` 或 `undefined` 必须根据业务转为默认值或丢弃，**严禁**写入字符串 "null" |
| **去重机制** | 在执行 `upsert` 之前，必须基于主键（如 `student_id`）检查冲突 |

### 批处理限制

* **单次 API 写入**: 不超过 **1000 条**
* **大批量数据**: 必须使用 **事务 (Transaction)** 或 **分片上传**
* **目的**: 防止半途失败导致数据不一致

---

## 3. 安全防污染 (Security Hygiene)

**目标**: 防止敏感信息泄露（污染代码库）。

### 🔑 零信任法则

| 规则 | 说明 |
|------|------|
| **禁止硬编码** | **严禁**将 `sk-xxx`, `postgres://password` 等密钥硬编码在 `.js`, `.py`, `.md` 文件中 |
| **环境变量** | 所有敏感信息必须从环境变量 (`process.env`) 读取 |
| **自检机制** | 提交代码前，Molt 必须自检是否包含 32 位以上的随机字符串（疑似 Key） |

### 🚫 数据库直连

* **再次重申**: 禁止在代码中使用 TCP 直连数据库（如 `pg_connect`）。
* **仅允许**: 通过 `Supabase Client` (REST API) 交互。

---

## 4. 逻辑防污染 (Logic Hygiene)

**目标**: 防止代码风格劣化（防御"屎山"代码）。

### Service 层封装

```javascript
// ❌ 禁止: 在 UI 组件中直接写数据库查询逻辑
const { data } = await supabase.from('table').select('*');

// ✅ 正确: 通过 Service Layer 封装
import userService from '@/services/userService';
const users = await userService.getAll();
```

### 注释规范

| 类型 | 要求 |
|------|------|
| 复杂逻辑 | 必须写明"为什么这么做"，而不仅仅是"做了什么" |
| TODO | 必须标记优先级（P0/P1），并在 `CLEAN_LOGIC.md` 中同步 |

---

## 5. 紧急熔断 (Emergency Kill Switch)

### 触发条件

| 条件 | 检测方式 |
|------|----------|
| API 调用耗费异常激增 | 死循环检测 |
| 数据库写入大量错误日志 | Error rate 异常 |

### 动作

1. 立即停止当前脚本
2. 输出 `EMERGENCY_STOP` 信号
3. 向指挥官报告

---

**维护者**: Molt (🦀)
**生效日期**: 2026-02-18
**最后更新**: 2026-02-18 13:25 GMT+8
