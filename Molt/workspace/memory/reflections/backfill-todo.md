
# Backfill Todo - 知识库补漏清单

## 已覆盖范围

### ✅ 已迁移到 kb/ 的内容
- **preferences/user.md**: 指挥官特征/偏好
- **people/user-profile.md**: 个人信息
- **projects/main.md**: Operation Nexus V4.1.2
- **decisions/**: 5 个决策记录（2026-02-21 ~ 2026-03-01）
- **lessons/**: 5 个经验教训（mcp-config, qmd-env, config, git, ops）

### ✅ 已覆盖的日期范围
- 2026-02-16 ~ 2026-03-01（重大事件/里程碑）
- 配置/MCP/Git/运维相关经验

---

## 候选补漏列表（待评估）

| # | 内容 | 来源 | 证据 | 优先级 |
|---|------|------|------|--------|
| 1 | OpenClaw 引擎飞升详细记录（Gemini 3.1, 火山引擎等） | MEMORY.full.md | "## 🚀 引擎飞升记录" 段落 | P2 |
| 2 | Cron 配置规范详情 | MEMORY.full.md | "## Cron 配置规范" 段落 | P3 |
| 3 | GLM-4.7 API 配置（脱敏版） | MEMORY.full.md | "## GLM-4.7 API 配置" 段落 | P3 |
| 4 | 技能状态清单 | MEMORY.full.md | "## 技能状态" 段落 | P3 |
| 5 | QMD 环境变量详细配置 | MEMORY.full.md | "## QMD 环境变量规范" 段落 | P2 |
| 6 | 双子星系统运维（已退役，历史参考） | MEMORY.full.md | "双子星系统运维（OpenClaw 多实例）" 段落 | P3 |
| 7 | Ubuntu 24.04 SSH 配置经验 | MEMORY.full.md | "Ubuntu 24.04 的 SSH 服务名称" | P2 |
| 8 | 火山引擎海外节点镜像源问题 | MEMORY.full.md | "火山引擎海外节点镜像源问题" 段落 | P2 |
| 9 | 交换内存配置（Linux）详细步骤 | MEMORY.full.md | "交换内存配置（Linux）" 段落 | P3 |
| 10 | OpenClaw 运行时缓存文件安全 | MEMORY.full.md | "OpenClaw 运行时缓存文件安全" 段落 | P2 |

---

## 补漏原则

1. **优先级判定**：
   - P1: 当前活跃使用，影响日常工作
   - P2: 有一定使用频率，按需补充
   - P3: 低频使用，可暂缓

2. **迁移条件**：
   - 必须有明确的 MEMORY.full.md 来源
   - 必须带 source/evidence 元数据
   - 遵循 read-first-CRUD 原则

3. **暂不迁移**：
   - 已退役系统（如双子星系统）
   - 敏感信息（如 API Key 实际值）
   - 动态状态（如待办事项）

---

*Created: 2026-03-01 13:58 (Asia/Shanghai)*
