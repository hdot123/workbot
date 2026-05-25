# Supermemory 记忆层集成分析报告

> 来源：https://github.com/supermemoryai/supermemory
> 阅读方式：4 次阅读（2 次 gpt-web-to + 2 次主线程交替）
> 整理时间：2026-03-23
> 用途：AEdu 项目记忆层集成评估

---

## 一、核心架构总览

| 层级 | 功能 | 性能 |
|------|------|------|
| **记忆引擎** | Graph Memory（Updates/Extends/Derives） | 自动提取、进化、遗忘 |
| **用户 Profile** | Static + Dynamic 双模事实 | ~50ms 响应 |
| **Hybrid Search** | RAG + Memory 统一查询 | 混合检索 |
| **Connectors** | Google Drive/Gmail/Notion/GitHub | Webhook 实时 + 4h 轮询 |

**核心洞察**：Supermemory 不是 RAG，而是**记忆 + RAG 的统一平台**。RAG 检索文档片段，Memory 提取用户事实。

---

## 二、Graph Memory 三层关系

### 2.1 关系类型

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory Relationships                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Updates（更新）                                          │
│     "Alex works at Google" → "Alex works at Stripe"        │
│     → isLatest 标记，历史保留，查询返回最新                  │
│                                                             │
│  2. Extends（扩展）                                          │
│     "Alex is PM at Stripe" + "Alex leads payments team"    │
│     → 两者共存，enriches 查询结果                           │
│                                                             │
│  3. Derives（推导）                                          │
│     "Alex is PM" + "Alex discusses payments frequently"    │
│     → "Alex likely works on core payments"                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 自动提取示例

**输入**：
> "Had a great call with Alex. He's enjoying the new PM role at Stripe, though the
> payments infrastructure work is intense. He moved to Seattle for the job—got a
> place in Capitol Hill. Wants to grab dinner next time I'm in town."

**提取的记忆**：
- Alex works at Stripe as a PM
- Alex works on payments infrastructure *(extends role memory)*
- Alex lives in Seattle, Capitol Hill *(new fact)*
- Alex wants to meet for dinner *(episodic)*

---

## 三、自动遗忘机制

| 记忆类型 | 示例 | 生命周期 |
|---------|------|---------|
| **Facts** | "Alex is PM at Stripe" | 持久，直到被 Update |
| **Preferences** | "Prefers dark mode" | 随重复强化 |
| **Episodes** | "Meeting Tuesday 3pm" | 时间过期后自动遗忘 |

**时间触发逻辑**：
```
"我明天有考试" → 考试日期过后 → 自动遗忘
"下午 3 点会议" → 当天过后 → 自动遗忘
```

**关键能力**：
- 矛盾解决：新事实自动标记为 latest
- 噪声过滤：casual content 不成为永久记忆
- 时间感知：查询时自动过滤过期信息

---

## 四、用户 Profile 系统

### 4.1 Profile 结构

```
┌──────────────────────────────────────────┐
│           User Profile                   │
├──────────────────────────────────────────┤
│  Static Facts（长期稳定）                  │
│  - "Senior engineer at TechCorp"         │
│  - "Prefers functional patterns"         │
│  - "Uses Vim"                            │
│                                          │
│  Dynamic Facts（近期上下文）               │
│  - "Migrating auth to microservices"     │
│  - "Debugging memory leak"               │
│  - "Preparing conference talk"           │
└──────────────────────────────────────────┘
```

### 4.2 API 调用

```typescript
const { profile, searchResults } = await client.profile({
  containerTag: "user_123",
  q: "programming style"  // 可选：同时搜索相关记忆
});

// profile.static  → 长期事实
// profile.dynamic → 近期上下文
// searchResults   → 相关记忆（如果传了 q）
```

### 4.3 触发条件

- 每次 `client.add()` 后触发提取
- AI 分析内容 → 抽取 facts → 更新 profile
- 批量/单次无区别，实时处理
- 响应时间：~50ms

---

## 五、Hybrid Search 原理

### 5.1 搜索流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid Search Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Query: "What phone should I recommend?"                    │
│                                                             │
│  Step 1: Entity Recognition → Identify "user_123"          │
│  Step 2: Graph Traversal → User preferences (Memory)       │
│  Step 3: Vector Search → Product specs (RAG)               │
│  Step 4: Temporal Filtering → Remove outdated facts        │
│  Step 5: Context Assembly → Merge results                  │
│                                                             │
│  Result:                                                    │
│  - Memory: "User prefers Android" (current, not old iOS)  │
│  - RAG: Latest Android phone specs                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Search Mode

```typescript
// Hybrid（默认）- RAG + Memory
await client.search.memories({
  q: "deploy",
  containerTag: "user_123",
  searchMode: "hybrid"
})

// Memories only - 仅用户记忆
await client.search.memories({
  q: "preferences",
  containerTag: "user_123",
  searchMode: "memories"
})
```

---

## 六、Memory vs RAG 核心区别

### 6.1 对比表

| 维度 | RAG | Memory |
|------|-----|--------|
| **本质** | 文档检索 | 事实提取 |
| **状态** | Stateless | Stateful |
| **时间感知** | 无 | 有（temporal validity） |
| **个性化** | 无 | 用户/实体绑定 |
| **关系追踪** | 无 | Updates/Extends/Derives |

### 6.2 经典场景

```
Day 1: "I love Adidas"
Day 30: "Adidas broke, switching to Puma"
Day 45: "Recommend sneakers?"

RAG 返回："I love Adidas"（语义最相似）❌
Memory 返回："Prefers Puma"（当前状态）✅
```

### 6.3 关键洞察

> **RAG answers "What do I know?" while Memory answers "What do I remember about you?"**

---

## 七、Connectors 同步机制

### 7.1 支持的 Connector

| Provider | 实时同步 | 定时同步 | 手动同步 |
|----------|---------|---------|---------|
| Google Drive | ✅ Webhooks (7 天过期) | ✅ 4h | ✅ |
| Gmail | ✅ Pub/Sub | ✅ 4h | ✅ |
| Notion | ✅ Webhooks | ✅ 4h | ✅ |
| OneDrive | ✅ Webhooks (30 天) | ✅ 4h | ✅ |
| GitHub | ✅ Webhooks | ✅ 4h | ✅ |
| Web Crawler | ❌ | ✅ Scheduled (7+ 天) | ✅ |

### 7.2 OAuth 流程

```typescript
// 1. Create connection
const connection = await client.connections.create('notion', {
  redirectUrl: 'https://yourapp.com/callback',
  containerTags: ['user-123'],
  documentLimit: 5000
})

// 2. Redirect user to OAuth
console.log(connection.authLink)

// 3. Sync begins automatically after OAuth complete
```

### 7.3 删除连接

```typescript
// 删除连接 + 删除导入的文档（默认）
await client.connections.deleteByID(connectionId)

// 删除连接 + 保留文档
await client.connections.deleteByID(connectionId, {
  deleteDocuments: false
})
```

---

## 八、AEdu 项目集成建议

### 8.1 集成场景映射

| AEdu 模块 | 记忆层用途 | Supermemory 功能 |
|----------|-----------|-----------------|
| **学生数字孪生** | 学习偏好、能力变化 | Profile 系统 |
| **观察层** | 家长/老师/学校多视角 | Graph Memory |
| **事件流** | 多源学习数据接入 | Connectors |
| **推演层** | 历史 + 文档统一检索 | Hybrid Search |
| **记忆与图谱** | 知识点掌握追踪 | Updates 关系 |

### 8.2 推荐 API 调用模式

```typescript
import Supermemory from "supermemory"

const client = new Supermemory({ apiKey: "sm_xxx" })

// 1. 记录学生学习事件
await client.add({
  content: "Student #123 在物理力学单元表现优秀，偏好图形化学习",
  containerTag: "student_123",
  metadata: { type: "learning_event", subject: "physics" }
})

// 2. 获取学生 Profile + 相关记忆
const { profile, searchResults } = await client.profile({
  containerTag: "student_123",
  q: "学习偏好"
})

// profile.static  → 学科能力、知识点掌握
// profile.dynamic → 近期学习重点
// searchResults   → 相关学习事件

// 3. Hybrid Search（学生记忆 + 教学文档）
const results = await client.search.memories({
  q: "如何提升力学理解",
  containerTag: "student_123",
  searchMode: "hybrid"
})
```

### 8.3 containerTag 设计

```
按学生：student_{id}
按班级：class_{id}
按学校：school_{id}
按项目：project_{id}
```

### 8.4 记忆类型映射

| AEdu 数据 | Supermemory 类型 | 行为 |
|----------|-----------------|------|
| 知识点掌握 | Fact | 持久，直到更新 |
| 学习风格 | Preference | 随重复强化 |
| 课程参与 | Episode | 时间过期遗忘 |
| 能力变化 | Fact (Updates) | 追踪最新状态 |

### 8.5 自动遗忘配置

```typescript
// 临时事件：考试安排
await client.add({
  content: "Student #123 明天有期中考试",
  containerTag: "student_123",
  metadata: {
    type: "episode",
    expiresAt: "2026-03-24"  // 考试后自动遗忘
  }
})

// 能力变化：物理成绩提升
await client.add({
  content: "Student #123 物理成绩从 B 提升到 A",
  containerTag: "student_123",
  metadata: {
    type: "fact",
    supersedes: "memory_abc123"  // Updates 关系
  }
})
```

---

## 九、API 认证与定价

### 9.1 获取 API Key

1. 访问：https://console.supermemory.ai
2. 注册账号
3. 创建项目
4. 获取 API Key（格式：`sm_xxx`）

### 9.2 认证方式

```typescript
// API Key 认证
const client = new Supermemory({ apiKey: "sm_xxx" })

// 或 HTTP Header
Authorization: Bearer sm_xxx
```

### 9.3 免费额度

> 需确认：文档未明确免费额度，建议注册后查看 Dashboard

---

## 十、下一步动作

| 序号 | 动作 | 负责人 | 状态 |
|------|------|--------|------|
| 1 | 创建 Supermemory 账号 | 项目负责人 | ⬜ 待办 |
| 2 | 获取 API Key | 项目负责人 | ⬜ 待办 |
| 3 | 安装 SDK (`npm install supermemory`) | 开发团队 | ⬜ 待办 |
| 4 | 用 AEdu 样例数据测试 Graph Memory | 开发团队 | ⬜ 待办 |
| 5 | 验证 Profile 注入延迟 (~50ms) | QA 团队 | ⬜ 待办 |
| 6 | 评估 Connector 需求（是否接入外部学习平台） | 产品团队 | ⬜ 待办 |
| 7 | 设计 containerTag 命名规范 | 架构团队 | ⬜ 待办 |

---

## 十一、风险与考量

### 11.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| API 依赖 | 服务不可用导致记忆层失效 | 本地缓存 + 降级策略 |
| 数据隐私 | 学生数据上云 | 评估合规性，考虑私有化部署 |
| 延迟敏感 | Profile 调用 >100ms 影响体验 | 预加载 + 本地缓存 |

### 11.2 成本考量

- API 调用计费模式待确认
- Connectors 同步可能产生额外费用
- 长期存储成本需评估

### 11.3 备选方案

如果 Supermemory 不满足需求，备选方案：
1. **Mem0** - 开源记忆层
2. **Zep** - 对话记忆平台
3. **自研** - 基于 Graph DB + Vector DB

---

## 十二、参考链接

- **官方文档**：https://supermemory.ai/docs
- **Quickstart**：https://supermemory.ai/docs/quickstart
- **Dashboard**：https://console.supermemory.ai
- **GitHub**：https://github.com/supermemoryai/supermemory
- **Discord**：https://supermemory.link/discord

---

**维护人**：项目负责人
**版本**：V1.0
**最后更新**：2026-03-23
**下次评审**：集成测试完成后
