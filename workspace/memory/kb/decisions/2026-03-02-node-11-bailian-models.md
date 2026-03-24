---
type: [KB:DECISION]
title: "node-11 百炼模型选择决策"
created: 2026-03-02 14:54
updated: 2026-03-02 14:54
source: Manual
confidence: high
tags: [node-11, bailian, models, decision, dev-bot, qa-bot]
related: [node-11, ubuntu-openclaw-deployment]
version: v1.0
status: active
last_verified: 2026-03-02
---

# node-11 百炼模型选择决策

## 📋 决策信息

- **决策日期**: 2026-03-02
- **决策者**: HT（指挥官）
- **执行者**: Molt 国王
- **决策类型**: 模型选择
- **影响范围**: node-11 计算节点
- **不可逆性**: 低（可随时调整模型优先级）

---

## 🎯 决策内容

### Dev Bot 模型配置
- **主模型**: bailian/coder-next
- **回退模型**: bailian/coder-plus → bailian/qwen3-max → bailian/glm-5
- **用途**: 开发任务

**模型优先级理由**:
1. **coder-next**: 最新的代码模型，适合开发任务
2. **coder-plus**: 次优选择，稳定可靠
3. **qwen3-max**: 通用大模型，适合复杂推理
4. **glm-5**: 最后的回退选项

### QA Bot 模型配置
- **主模型**: bailian/coder-plus
- **回退模型**: bailian/coder-next → bailian/qwen3-max → bailian/glm-4.7
- **用途**: QA 任务

**模型优先级理由**:
1. **coder-plus**: 稳定的代码模型，适合 QA 任务
2. **coder-next**: 次优选择，尝试新特性
3. **qwen3-max**: 通用大模型，适合复杂推理
4. **glm-4.7**: 最后的回退选项（QA 使用 4.7 而不是 5.0）

---

## 💡 决策依据

### 为什么选择百炼 Coding Plan？
1. **成本优势**: Coding Plan 套餐性价比高
2. **模型质量**: 百炼的代码模型质量好
3. **API 兼容**: 支持 OpenAI 兼容 API，易于集成
4. **网络稳定**: 国内访问稳定，延迟低

### 为什么 Dev 和 QA 使用不同的模型优先级？
1. **Dev Bot**: 
   - 优先使用最新的 coder-next，追求最佳效果
   - 适合探索性开发，可以容忍一定的不稳定性

2. **QA Bot**:
   - 优先使用稳定的 coder-plus，追求可靠性
   - 适合自动化测试，需要稳定一致的输出
   - 回退到 glm-4.7 而不是 5.0，因为 QA 任务不需要最新模型

### 为什么使用共享 API Key？
1. **简化管理**: 只需管理一个 Key
2. **成本控制**: 统一计费，便于监控
3. **权限统一**: 所有 bot 使用相同的权限级别

---

## 📊 影响评估

### 正面影响
1. **开发效率**: Dev Bot 使用最新模型，提高开发效率
2. **QA 稳定性**: QA Bot 使用稳定模型，提高测试可靠性
3. **成本优化**: Coding Plan 套餐性价比高
4. **易于维护**: 共享 API Key，简化管理

### 潜在风险
1. **API Key 泄露**: 共享 Key 泄露影响所有 bot
   - **缓解措施**: 定期更换 Key，监控使用情况
2. **模型不稳定**: coder-next 可能不够稳定
   - **缓解措施**: 配置多个回退模型
3. **API 配额耗尽**: 所有 bot 共享配额
   - **缓解措施**: 监控配额使用，设置告警

---

## 🔄 替代方案

### 方案 1: 使用不同的 API Key
- **优点**: 权限隔离，风险分散
- **缺点**: 管理复杂，成本可能更高
- **决策**: 不采用，共享 Key 更简单

### 方案 2: Dev 和 QA 使用相同的模型优先级
- **优点**: 配置简单，一致性高
- **缺点**: 无法针对不同任务优化
- **决策**: 不采用，不同任务需要不同的模型策略

### 方案 3: 使用其他模型提供商
- **优点**: 可能有更好的模型或价格
- **缺点**: 需要重新评估和集成
- **决策**: 暂不采用，百炼已满足需求

---

## 📅 实施计划

### 已完成
- [x] 创建 dev-bot 用户和配置
- [x] 创建 qa-bot 用户和配置
- [x] 创建 reserved 用户和配置（未启动）
- [x] 配置 systemd 服务
- [x] 启动 dev-bot 和 qa-bot 服务
- [x] 验证服务正常运行

### 待完成
- [ ] 监控 API 使用情况
- [ ] 测试模型调用和 failover
- [ ] 根据实际使用情况调整模型优先级

---

## 📚 相关文档

- **node-11 持续手册**: `workspace/memory/kb/projects/node-11.md`
- **Ubuntu OpenClaw 部署经验**: `workspace/memory/kb/lessons/ubuntu-openclaw-deployment.md`

---

## 🔄 更新历史

- **2026-03-02 14:54**: 初始创建，记录 node-11 百炼模型选择决策
