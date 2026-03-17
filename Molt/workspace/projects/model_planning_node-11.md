# 模型规划 - node-11 多租客环境

**规划日期**: 2026-02-28
**目标**: 为node-11上的三个租客（user1, user2, user3）配置合适的模型

---

## 📊 当前可用的模型资源

### 1. 智谱 AI（Zhipu AI）- 包年计划 ⭐ **主力模型提供商**

**提供商**: 智谱 AI
**计划类型**: 包年计划
**API 端点**: `https://open.bigmodel.cn/api/anthropic`

**可用模型**:
- `glm-5` - **最新旗舰模型**
  - 特点：性能强大，支持长上下文
  - 推荐：✅ **作为主力模型**
  
- `glm-4.7` - 稳定版本
  - 特点：稳定性好，性能可靠
  - 推荐：作为备选模型

**优势**:
- ✅ **包年计划，无限制使用**
- ✅ **性能强大，最新旗舰**
- ✅ **成本可控，已预付**

---

### 2. 阿里云百炼 Coding Plan - 包月 🌐 **模型聚合平台**

**提供商**: 阿里云（Alibaba Cloud）
**计划类型**: 包月计划
**特点**: 模型聚合平台，提供多种模型选择

#### 2.1 通义千问系列（阿里云自研）

**qwen3.5-plus** 🎨 **多模态模型**
- 特点：**支持图片理解**
- 推荐：✅ **多模态任务（文本+图像）**

**qwen3-max-2026-01-23** 🚀 **旗舰模型**
- 特点：最新版本，性能强大
- 推荐：✅ **通用任务**

**qwen3-coder-next** 🔧 **编程模型（下一代）**
- 特点：编程专用，下一代版本
- 推荐：🔧 **编程任务（最新）**

**qwen3-coder-plus** 💻 **编程模型（增强版）**
- 特点：编程专用，增强版
- 推荐：💻 **编程任务（稳定）**

#### 2.2 第三方模型

**kimi-k2.5** 🎨 **多模态模型**
- 特点：**支持图片理解**
- 推荐：✅ **多模态任务（文本+图像）**

**glm-5** 🤖 **智谱模型**
- 特点：智谱GLM-5（通过阿里云百炼）
- 推荐：🤖 **通用任务**

**MiniMax-M2.5** 🔮 **MiniMax模型**
- 特点：MiniMax最新模型
- 推荐：🔮 **通用任务**

**glm-4.7** 🤖 **智谱模型（稳定版）**
- 特点：智谱GLM-4.7（通过阿里云百炼）
- 推荐：🤖 **通用任务（稳定）**

---

## 🎯 配置策略建议

### 💡 **推荐配置方案：差异化配置**

根据三个租客的不同用途，配置不同的模型：

#### **user1 - 通用任务** 📝

**主力模型**: `glm-5`（智谱 AI，包年计划）
**备用模型**: `qwen3-max-2026-01-23`（阿里云百炼，包月）

**配置**:
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-5",
        "fallback": "qwen3-max-2026-01-23"
      }
    }
  }
}
```

**理由**:
- ✅ **主力模型**：智谱GLM-5，包年计划无限制使用
- ✅ **备用模型**：通义千问最新版，性能强大
- ✅ **成本优化**：优先使用包年计划，备用使用包月计划

---

#### **user2 - 编程任务** 💻

**主力模型**: `qwen3-coder-plus`（阿里云百炼，包月）
**备用模型**: `glm-5`（智谱 AI，包年）

**配置**:
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "qwen3-coder-plus",
        "fallback": "zai/glm-5"
      }
    }
  }
}
```

**理由**:
- ✅ **主力模型**：通义千问编程专用模型，针对编程任务优化
- ✅ **备用模型**：智谱GLM-5，通用性能强大
- ✅ **专业优化**：编程任务使用专用模型，效果更好

---

#### **user3 - 多模态任务** 🎨

**主力模型**: `qwen3.5-plus`（阿里云百炼，包月）
**备用模型**: `kimi-k2.5`（阿里云百炼，包月）

**配置**:
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "qwen3.5-plus",
        "fallback": "kimi-k2.5"
      }
    }
  }
}
```

**理由**:
- ✅ **主力模型**：通义千问3.5-plus，支持图片理解
- ✅ **备用模型**：Kimi k2.5，也支持图片理解
- ✅ **多模态支持**：可以处理文本和图像

---

## 💰 成本优化策略

### 成本优先级

1. **智谱 AI（包年计划）** - **最高优先级** ⭐
   - 已预付，无限制使用
   - 优先用于所有通用任务

2. **阿里云百炼（包月计划）** - **次要优先级** 🔄
   - 包月限额，需要控制使用
   - 用于特殊任务（编程、多模态）

### 使用建议

- **通用任务**：优先使用智谱GLM-5（包年计划）
- **编程任务**：使用阿里云qwen3-coder-plus（包月计划）
- **多模态任务**：使用阿里云qwen3.5-plus（包月计划）
- **故障转移**：智谱GLM-5作为备用模型

---

## 🔑 API Key 管理方案

### 方案1：环境变量（推荐）⭐

**优点**:
- 安全性高
- 不暴露在配置文件中
- 便于管理

**配置**:
```bash
# 在每个用户的 ~/.bashrc 或 ~/.profile 中
export ZHIPU_API_KEY="your_zhipu_api_key"
export ALIBABA_API_KEY="your_alibaba_api_key"
```

**openclaw.json**:
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-5"
      }
    }
  },
  "remote": {
    "baseUrl": "https://open.bigmodel.cn/api/anthropic",
    "apiKey": "${ZHIPU_API_KEY}"
  }
}
```

---

## 📋 实施步骤

### 步骤1：配置环境变量

```bash
# 为每个用户配置环境变量
su - user1 -c 'echo "export ZHIPU_API_KEY=your_key" >> ~/.bashrc'
su - user2 -c 'echo "export ALIBABA_API_KEY=your_key" >> ~/.bashrc'
su - user3 -c 'echo "export ALIBABA_API_KEY=your_key" >> ~/.bashrc'
```

### 步骤2：更新配置文件

```bash
# 为每个用户更新 openclaw.json
# 添加 model 配置（参考上面的配置示例）
```

### 步骤3：重启网关

```bash
# 重启所有租客的网关
su - user1 -c "pm2 restart openclaw-gateway"
su - user2 -c "pm2 restart openclaw-gateway"
su - user3 -c "pm2 restart openclaw-gateway"
```

### 步骤4：验证配置

```bash
# 测试模型连接
curl -X POST https://node-11.tail5e888.ts.net:18810/v1/chat/completions \
  -H "Authorization: Bearer user1-exclusive-token-19010" \
  -H "Content-Type: application/json" \
  -d '{"model": "zai/glm-5", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## 🚨 注意事项

1. **API Key 安全**:
   - ❌ 不要在配置文件中直接写入API Key
   - ✅ 使用环境变量
   - ✅ 定期轮换API Key

2. **成本控制**:
   - 监控每个租客的token使用量
   - 设置使用限额
   - 定期检查账单

3. **性能监控**:
   - 监控模型响应时间
   - 监控错误率
   - 设置告警机制

4. **备用方案**:
   - 配置备用模型
   - 准备故障转移方案
   - 定期测试备用模型

---

## 📊 模型对比表

| 模型 | 提供商 | 特点 | 适用场景 | 优先级 |
|------|--------|------|----------|--------|
| glm-5 | 智谱 AI | 最新旗舰，性能强大 | 通用任务 | ⭐⭐⭐⭐⭐ |
| glm-4.7 | 智谱 AI | 稳定版本 | 通用任务（稳定） | ⭐⭐⭐⭐ |
| qwen3.5-plus | 阿里云百炼 | **支持图片理解** | 多模态任务 | ⭐⭐⭐⭐⭐ |
| qwen3-max-2026-01-23 | 阿里云百炼 | 最新旗舰 | 通用任务 | ⭐⭐⭐⭐ |
| qwen3-coder-next | 阿里云百炼 | 编程专用（最新） | 编程任务 | ⭐⭐⭐⭐⭐ |
| qwen3-coder-plus | 阿里云百炼 | 编程专用（稳定） | 编程任务 | ⭐⭐⭐⭐ |
| kimi-k2.5 | 阿里云百炼 | **支持图片理解** | 多模态任务 | ⭐⭐⭐⭐ |
| MiniMax-M2.5 | 阿里云百炼 | MiniMax最新 | 通用任务 | ⭐⭐⭐ |

---

**文档版本**: 2.0
**最后更新**: 2026-02-28
**维护者**: Molt (战术蟹王)
