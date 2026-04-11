# Supermemory 记忆层阅读记录

> 来源：https://github.com/supermemoryai/supermemory
> 阅读时间：2026-03-23
> 阅读方式：4 次阅读（2 次 gpt-web-to + 2 次主线程交替）
> 目的：AEdu 项目记忆层集成评估

---

## 阅读记录

### 第一次阅读（gpt-web-to）

**Prompt**：
```
请帮我深度阅读并分析 supermemoryai/supermemory 项目，重点关注：
1. 记忆引擎工作原理（Graph Memory、Updates/Extends/Derives、与 RAG 的区别）
2. 用户 Profile 系统（用户记忆如何提取和存储、Profile 如何用于个性化）
3. Hybrid Search 机制（向量搜索 + 图搜索如何结合、搜索 API 的使用方法）
4. Connectors 集成方式（支持哪些数据源、如何接入外部数据）
```

**ChatGPT 响应摘要**：
- 优先读项目源码与官方文档
- 重点拆四块：记忆引擎、Profile、Hybrid Search、Connectors
- 用教学式说明呈现

---

### 第二次阅读（主线程）

**读取文件**：
1. `README.md` - 项目概述、核心功能、API  quickstart
2. `apps/docs/intro.mdx` - 记忆层概览、context engineering 定位
3. `apps/docs/concepts/graph-memory.mdx` - Graph Memory 三层关系详解
4. `apps/docs/memory-api/overview.mdx` - API 快速入门

**核心发现**：
- Graph Memory 三层关系：Updates（更新）、Extends（扩展）、Derives（推导）
- 自动遗忘机制：时间过期自动清除临时记忆
- Profile 系统：Static（长期事实）+ Dynamic（近期上下文）
- Hybrid Search：RAG + Memory 统一查询

---

### 第三次阅读（gpt-web-to）

**Prompt**：
```
从**集成者视角**深度分析：
1. 记忆层架构设计（三层关系如何实现记忆进化、自动遗忘机制、记忆类型生命周期）
2. 用户 Profile 系统技术细节（Static/Dynamic 分离、触发条件、~50ms 性能）
3. Hybrid Search 实现原理（RAG+Memory 融合、权重分配、searchMode 差异）
4. Connectors 数据同步机制（Webhook vs 轮询、去重冲突解决、统一 schema）
```

**ChatGPT 响应摘要**：
- 视角切换到"集成者/工程落地"
- 优先抓核心文档、API 文档和源码入口
- 重点回答触发机制、生命周期、同步与检索融合

---

### 第四次阅读（主线程）

**读取文件**：
1. `apps/docs/concepts/user-profiles.mdx` - Profile 系统详解
2. `apps/docs/concepts/memory-vs-rag.mdx` - Memory 与 RAG 的核心区别
3. `apps/docs/connectors/overview.mdx` - Connectors 同步机制

**核心发现**：

#### Profile 系统
- **Static Profile**：长期稳定事实（"Senior engineer at TechCorp"）
- **Dynamic Profile**：近期上下文（"Migrating auth to microservices"）
- **响应时间**：~50ms（传统搜索 200-500ms）
- **触发条件**：每次 `add()` 后实时提取

#### Memory vs RAG
| 维度 | RAG | Memory |
|------|-----|--------|
| 本质 | 文档检索 | 事实提取 |
| 状态 | Stateless | Stateful |
| 时间感知 | 无 | 有 |
| 个性化 | 无 | 用户绑定 |

**经典场景**：
```
Day 1: "I love Adidas"
Day 30: "Adidas broke, switching to Puma"
Day 45: "Recommend sneakers?"

RAG → "I love Adidas" ❌（语义最相似）
Memory → "Prefers Puma" ✅（当前状态）
```

#### Connectors 同步机制
| Provider | 实时同步 | 定时同步 |
|----------|---------|---------|
| Google Drive | ✅ Webhooks (7 天) | ✅ 4h |
| Gmail | ✅ Pub/Sub | ✅ 4h |
| Notion | ✅ Webhooks | ✅ 4h |
| OneDrive | ✅ Webhooks (30 天) | ✅ 4h |
| GitHub | ✅ Webhooks | ✅ 4h |
| Web Crawler | ❌ | ✅ Scheduled (7+ 天) |

---

## AEdu 集成建议

### 集成场景映射

| AEdu 模块 | 记忆层用途 | Supermemory 功能 |
|----------|-----------|-----------------|
| 学生数字孪生 | 学习偏好、能力变化 | Profile 系统 |
| 观察层 | 家长/老师/学校多视角 | Graph Memory |
| 事件流 | 多源学习数据接入 | Connectors |
| 推演层 | 历史 + 文档统一检索 | Hybrid Search |

### containerTag 设计
```
按学生：student_{id}
按班级：class_{id}
按学校：school_{id}
```

### 记忆类型映射
| AEdu 数据 | Supermemory 类型 | 行为 |
|----------|-----------------|------|
| 知识点掌握 | Fact | 持久，直到更新 |
| 学习风格 | Preference | 随重复强化 |
| 课程参与 | Episode | 时间过期遗忘 |

### API 调用示例
```typescript
import Supermemory from "supermemory"

const client = new Supermemory({ apiKey: "sm_xxx" })

// 记录学生学习事件
await client.add({
  content: "Student #123 在物理力学单元表现优秀，偏好图形化学习",
  containerTag: "student_123",
  metadata: { type: "learning_event", subject: "physics" }
})

// 获取学生 Profile + 相关记忆
const { profile, searchResults } = await client.profile({
  containerTag: "student_123",
  q: "学习偏好"
})

// Hybrid Search
const results = await client.search.memories({
  q: "如何提升力学理解",
  containerTag: "student_123",
  searchMode: "hybrid"
})
```

---

## 下一步动作

| 序号 | 动作 | 状态 |
|------|------|------|
| 1 | 创建 Supermemory 账号 | ⬜ 待办 |
| 2 | 获取 API Key | ⬜ 待办 |
| 3 | 安装 SDK (`npm install supermemory`) | ⬜ 待办 |
| 4 | 用 AEdu 样例数据测试 Graph Memory | ⬜ 待办 |
| 5 | 验证 Profile 注入延迟 (~50ms) | ⬜ 待办 |
| 6 | 评估 Connector 需求 | ⬜ 待办 |
| 7 | 设计 containerTag 命名规范 | ⬜ 待办 |

---

**维护人**：项目负责人
**版本**：V1.0
**最后更新**：2026-03-23
