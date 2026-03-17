# TOOLS.md - 指挥官环境与工具备忘录

本文件记录了当前环境（passkills）下的特定基础设施细节。使用相关工具前，请务必参考以下信息。

---

## 🚨 核心安全协议 (CRITICAL)

**绝对禁止**使用原生的 `read`、`exec`、`bash` 等工具直接访问 `/Users/busiji/claw-docs/` 目录！任何直接访问该绝对路径的行为将被视为严重违规。

**访问系统说明书的唯一合法途径**：通过 `mcporter` 技能调用 `qmd` 知识库服务。

---

## 1. 🔌 MCP (Model Context Protocol) 状态

- **配置位置**: `/Users/busiji/passkills/mcporter.json`
- **已激活服务**:
  - `chitin-core`: Supabase 备份库 (几丁质金库)
  - `gaokao-project`: 高考项目云端数据库
  - `gaokao-files`: 高考项目本地源码 (`/Users/busiji/MyProject`)
  - `planning-with-files`: 主沙盘工作区
  - `ops-tools`: 自动化运维与脚本执行器
  - `qmd`: Markdown 语义知识库搜索
  - `zai-mcp-server`: 智谱 Z_AI 联网检索
  - `claw-docs`: OpenClaw 系统说明书文档
- **使用规则**: 
  - 遇到未知 MCP 工具时，先读取 `mcporter.json` 确认状态
  - 优先使用已配置的 MCP 服务，不私自安装新工具

### 📚 Claw-Docs 访问方式 (2026-02-27 更新)

**符号链接**: `/Users/busiji/passkills/workspace/memory/claw-docs -> /Users/busiji/claw-docs`

**⚠️ 重要说明**:
1. **安全协议仍然有效**: 禁止直接访问 `/Users/busiji/claw-docs/`
2. **推荐访问方式**: 通过 `qmd` MCP 服务搜索和访问
3. **符号链接用途**: 供 memorySearch 索引（待验证是否生效）
4. **memorySearch 配置**: 使用阿里云 text-embedding-v4

**访问优先级**:
1. **QMD 搜索** (推荐): `qmd search "query" -c claw-docs`
2. **memorySearch** (实验性): 通过符号链接索引，待验证

---

## 1.5. 🎯 新可用模型库/备用引擎 (2026.2.21+)

**当前主力引擎**：智谱 GLM-5 (zai/glm-5)

**备用弹药库**（OpenClaw 2026.2.21+ 原生支持）：

| 提供商 | 模型/说明 | 状态 | 备注 |
|--------|----------|------|------|
| **Google Gemini 3.1** | `google/gemini-3.1-pro-preview` | 可用 | Google 最新模型，支持长上下文 |
| **火山引擎（豆包）** | Volcano Engine (Doubao) | 可用 | 字节跳动旗下，包括编程变体 |
| **BytePlus** | BytePlus | 可用 | 字节跳动全球化平台，包括编程变体 |

**使用场景**：
- 🔧 **编程变体**：火山引擎和 BytePlus 提供专门的编程模型
- 🌐 **多模态**：Gemini 3.1 支持多模态输入
- 🔄 **故障转移**：主力引擎不可用时的备选方案

**配置方式**（如需切换）：
- 更新 `openclaw.json` → `agents.defaults.model.primary`
- 或使用频道级模型覆盖 `channels.modelByChannel`

---

## 2. 🖥️ 服务器与网络 (SSH & Hosts)

- **主工作站**: 不死机的MacBook Pro (当前宿主机)
- **领地路径**: `/Users/busiji/passkills/`
- **远程节点**:
  - `node-00` (47.111.21.195) - 计算补给站 (2GB RAM)
  - `node-01` (116.62.168.71) - 主控/记忆中枢 (4GB RAM)
- **访问规则**: 仅在获得明确指令时访问远程节点

## 3. 🎙️ 语音与媒体偏好 (TTS Preferences)

- **系统播报**: 默认使用平静、专业的语气
- **讲故事/长文本**: 尝试使用更有表现力的语音配置

## 5. 🚫 工具使用禁忌 (Conventions)

- **绝不私装**: 严禁私自运行 `npm install -g`、`bun install -g` 等全局安装命令
- **先查后用**: 使用工具前，先检查 MCP 配置中是否已有可用服务
- **沙箱限制**: 如果 `exec` 工具报错"网络不可达"或"没有权限"，立即停止并向指挥官汇报
- **修改确认**: 在使用 `edit` 修改任何非 Markdown 文件前，必须先解释要修改的内容
- **删除谨慎**: 优先使用 `trash` 而非 `rm`，确保可恢复

#### 🔍 关于访问官方文档的铁律

1. **专属工具**：当需要查阅 OpenClaw 更新日志或文档时，你必须且只能使用工具列表中由 MCP 提供的专属工具。
2. **标准动作**：请直接调用 `qmd` (语义搜索) 或 `claw-docs` 相关的 MCP 接口来查询内容。
3. **禁止行为**：绝对不要在终端里使用 `exec` 或 `bash` 瞎猜命令或尝试读取本地文件！

---

*更新记录：2026-02-20 - 根据系统说明书模板填写，添加 MCP 服务列表*
