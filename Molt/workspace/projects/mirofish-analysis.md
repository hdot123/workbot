# MiroFish 项目深度分析报告

**分析日期**: 2026-03-10
**项目地址**: https://github.com/666ghj/MiroFish
**分析者**: Claude (Sonnet 4.6)

---

## 📊 项目核心概览

### 定位与愿景

**MiroFish** 是一个基于多智能体技术的 AI 预测引擎，核心理念：

- **映射现实**：从现实世界提取"种子信息"（新闻、政策、金融信号）
- **构建平行世界**：创建高保真的数字世界
- **群体涌现**：数千个具备独立人格、长期记忆的智能体进行社会演化
- **预测未来**：通过"上帝视角"动态注入变量，推演未来走向

**口号**：*"让未来在数字沙盘中预演，助决策在百战模拟后胜出"*

---

## 🏗️ 技术栈全景图

### 前端架构 (Vue 3 生态)

```
frontend/src/
├── api/           # API 调用层
├── components/    # Vue 组件库
├── views/         # 页面视图
├── router/        # Vue Router 路由
├── store/         # 状态管理
├── assets/        # 静态资源
├── App.vue        # 根组件
└── main.js        # 入口文件
```

### 后端架构 (Python Flask)

**核心依赖**：

```python
# ============= 核心框架 =============
flask>=3.0.0           # Web 框架
flask-cors>=6.0.0      # 跨域支持

# ============= LLM 相关 =============
openai>=1.0.0          # 统一使用 OpenAI SDK 格式调用 LLM

# ============= 记忆系统 =============
zep-cloud==3.13.0      # 长期记忆管理

# ============= OASIS 社交媒体模拟 (核心!) =============
camel-oasis==0.2.5     # OASIS 社交模拟框架
camel-ai==0.2.78       # CAMEL-AI 框架

# ============= 文件处理 =============
PyMuPDF>=1.24.0        # PDF 处理
charset-normalizer>=3.0.0  # 编码检测
chardet>=5.0.0

# ============= 工具库 =============
python-dotenv>=1.0.0   # 环境变量
pydantic>=2.0.0        # 数据验证
```

**后端目录结构**：

```
backend/
├── app/
│   ├── __init__.py      # Flask 应用工厂
│   ├── api/             # API 路由
│   ├── services/        # 核心业务逻辑
│   ├── models/          # 数据模型
│   ├── utils/           # 工具函数
│   └── config.py        # 配置管理
├── run.py               # 启动入口
├── requirements.txt     # 依赖列表
├── pyproject.toml       # 项目配置
└── scripts/             # 脚本工具
```

---

## 🧠 核心架构设计

### 1. 四大核心模块

#### A. 图谱构建模块 (GraphRAG)
- **现实种子提取**：从上传的文档中提取关键实体和关系
- **记忆注入**：使用 **Zep Cloud** 管理智能体的长期记忆
- **GraphRAG 构建**：构建知识图谱 + RAG 检索增强生成

#### B. 环境搭建模块
- **实体关系抽取**：使用 LLM 提取文档中的人物关系
- **人设生成**：为每个智能体生成独特的人格、背景、价值观
- **环境配置 Agent**：自动注入仿真参数

#### C. 仿真模拟模块 (OASIS)
- **双平台并行模拟**：可能同时在多个平台上运行仿真
- **自动解析预测需求**：根据用户问题自动调整仿真方向
- **时序记忆更新**：动态更新智能体的记忆

#### D. 报告生成模块
- **ReportAgent**：专门负责生成预测报告
- **丰富工具集**：可与模拟环境深度交互
- **深度互动**：用户可与任意智能体对话

---

## 🔄 完整工作流程

```
用户上传种子材料
    ↓
图谱构建 (GraphRAG + Zep 记忆注入)
    ↓
实体关系抽取
    ↓
智能体人设生成
    ↓
环境配置
    ↓
OASIS 仿真启动
    ↓
智能体自由交互
    ↓
群体涌现现象
    ↓
ReportAgent 分析
    ↓
生成预测报告
    ↓
用户深度互动
```

**详细流程**：

1. **图谱构建**：现实种子提取 & 个体与群体记忆注入 & GraphRAG 构建
2. **环境搭建**：实体关系抽取 & 人设生成 & 环境配置 Agent 注入仿真参数
3. **开始模拟**：双平台并行模拟 & 自动解析预测需求 & 动态更新时序记忆
4. **报告生成**：ReportAgent 拥有丰富的工具集与模拟后环境进行深度交互
5. **深度互动**：与模拟世界中的任意一位进行对话 & 与 ReportAgent 进行对话

---

## 🎯 关键技术亮点

### 1. OASIS 社交媒体仿真引擎

这是整个系统的**核心引擎**，来自 CAMEL-AI 团队：

```python
camel-oasis==0.2.5
camel-ai==0.2.78
```

**OASIS 能力**：
- 模拟社交媒体环境（类似 Twitter/Reddit）
- 智能体可以发布内容、评论、点赞
- 模拟信息传播、舆论演化
- 支持多种人格和行为模式

### 2. Zep Cloud 记忆系统

```python
zep-cloud==3.13.0
```

**作用**：
- 为每个智能体提供**长期记忆**
- 支持记忆检索和更新
- 保持智能体行为的连贯性
- 每月有免费额度

### 3. 多智能体架构

每个智能体具备：
- ✅ **独立人格**（通过 LLM 生成）
- ✅ **长期记忆**（Zep Cloud）
- ✅ **行为逻辑**（基于人设）
- ✅ **自由交互**（通过 OASIS）

---

## 💡 应用场景分析

### 场景 1: 舆情预测

```
输入: 武汉大学舆情报告
过程: 生成数百个代表不同利益群体的智能体
      在 OASIS 中模拟舆论传播
输出: 预测舆情走向、关键节点、风险点
```

### 场景 2: 文学创作推演

```
输入: 《红楼梦》前80回
过程: 提取人物关系图谱
      生成符合原著人设的智能体
      在虚拟环境中自由演化
输出: 预测失传的结局
```

### 场景 3: 政策影响预测

```
输入: 政策草案 + 社会背景数据
过程: 生成不同群体的智能体
      模拟政策发布后的社会反应
输出: 政策效果的预评估
```

---

## 🔧 部署架构

### 启动入口 (run.py 分析)

```python
"""
MiroFish Backend 启动入口
"""
import os
import sys

# 解决 Windows 控制台中文乱码问题
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

def main():
    """主函数"""
    # 验证配置
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f" - {err}")
        print("\n请检查 .env 文件中的配置")
        sys.exit(1)

    # 创建应用
    app = create_app()

    # 获取运行配置
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG

    # 启动服务
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    main()
```

**关键点**：
- 使用 **Flask 应用工厂模式** (`create_app()`)
- 支持环境变量配置
- 默认运行在 `0.0.0.0:5001`
- 多线程模式 (`threaded=True`)

### 开发环境

```bash
# 前端: http://localhost:3000
# 后端: http://localhost:5001
```

### Docker 部署

```yaml
# docker-compose.yml
services:
  frontend:
    port: 3000
  backend:
    port: 5001
    environment:
      - LLM_API_KEY
      - LLM_BASE_URL
      - ZEP_API_KEY
```

### 关键配置

```bash
# LLM 配置 (推荐阿里百炼 qwen-plus)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# 记忆系统
ZEP_API_KEY=your_zep_api_key
```

---

## 🎨 设计哲学

### 1. 群体智能

- 不依赖单一智能体
- 通过**大规模交互**涌现出集体智慧
- 模拟真实社会的复杂性

### 2. 平行世界

- 数字世界 = 现实世界的镜像
- 可以在零风险环境中试错
- "让未来在数字沙盘中预演"

### 3. 可解释性

- 用户可以与任意智能体对话
- ReportAgent 提供详细分析
- 不是黑盒预测，而是透明的推演过程

---

## 🚀 核心优势

| 优势 | 说明 |
|------|------|
| **通用性** | 可预测任何有"种子信息"的事物 |
| **可交互性** | 深度对话式探索 |
| **高保真** | 基于 GraphRAG + 长期记忆 |
| **零风险** | 在虚拟环境中试错 |
| **涌现性** | 群体行为不可预测，但符合统计规律 |

---

## 📈 项目成熟度

- ✅ 已有在线 Demo
- ✅ Docker 一键部署
- ✅ 详细文档
- ✅ 盛大集团战略支持
- ✅ 招募全职/实习生
- ✅ GitHub Trending 榜首

---

## 🎓 学习价值

这个项目非常适合学习：

1. **多智能体系统设计**
2. **LLM 应用架构** (RAG + Agent + Memory)
3. **社会仿真** (OASIS 引擎)
4. **知识图谱构建**
5. **群体智能** 涌现机制

---

## 🔍 与 BettaFish 的关系

根据 Web 搜索结果，还有一个相关项目 **BettaFish**：

- **BettaFish**：负责数据收集和分析
- **MiroFish**：负责全景预测

两者形成完整的数据→预测流水线。

---

## 📊 技术架构对比

### 与传统预测方法的对比

| 维度 | 传统预测 | MiroFish |
|------|---------|----------|
| **方法** | 统计模型、时间序列 | 多智能体仿真 |
| **输入** | 历史数据 | 种子信息 + 文档 |
| **输出** | 点预测 | 场景推演 + 互动 |
| **可解释性** | 低 | 高（可与智能体对话） |
| **适应性** | 需要重新训练 | 动态调整 |

---

## 🚨 潜在挑战

### 1. 成本问题

- 大规模智能体仿真消耗大量 LLM API 调用
- 推荐先进行小于 40 轮的模拟测试

### 2. 质量控制

- 智能体行为的一致性
- 预测结果的验证
- 记忆系统的可靠性

### 3. 可扩展性

- 大规模仿真的性能优化
- 多平台并行的调度策略

---

## 总结

**MiroFish 是一个极具创新性的群体智能预测平台**，它巧妙地结合了：

- 🧠 **LLM** (大语言模型)
- 🤖 **Multi-Agent** (多智能体)
- 🌐 **Social Simulation** (社会仿真)
- 💾 **Long-term Memory** (长期记忆)
- 📊 **Knowledge Graph** (知识图谱)

它的核心价值在于**将不可预测的未来，通过大规模智能体仿真，变成可以在数字沙盘中预演的场景**。

---

## 📚 参考资源

- **GitHub 仓库**: https://github.com/666ghj/MiroFish
- **在线 Demo**: mirofish-live-demo
- **CAMEL-AI**: https://github.com/camel-ai/camel
- **Zep Cloud**: https://www.getzep.com/

---

**分析状态**: ✅ 已完成
**最后更新**: 2026-03-10
**分析者**: Claude (Sonnet 4.6)
