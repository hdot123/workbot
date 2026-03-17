# OpenClaw 多代理路由

> 官方文档: https://docs.openclaw.ai/concepts/multi-agent
> 版本: 2026.2.13 | 日期: 2026-02-16

---

## 概述

目标：多个**隔离**代理 (独立workspace + `agentDir` + sessions)，加上多个channel账户 (例如两个WhatsApp) 在一个运行中的Gateway。入站通过bindings路由到代理。

---

## 什么是"一个代理"？

一个**代理**是一个完全独立的大脑，有自己的：

- **Workspace** (文件, AGENTS.md/SOUL.md/USER.md, 本地笔记, 人格规则)
- **状态目录** (`agentDir`) 用于认证配置、模型注册和代理配置
- **会话存储** (聊天历史 + 路由状态) 在 `~/.openclaw/agents/<agentId>/sessions`

认证配置是**每个代理**的。每个代理从自己的位置读取：

```
~/.openclaw/agents/<agentId>/agent/auth-profiles.json
```

主代理凭证**不会**自动共享。永远不要跨代理重用 `agentDir` (会导致认证/会话冲突)。

Skills通过每个workspace的 `skills/` 文件夹按代理配置，共享skills从 `~/.openclaw/skills` 获取。

---

## 路径快速映射

| 项目 | 路径 |
|------|------|
| 配置 | `~/.openclaw/openclaw.json` |
| 状态目录 | `~/.openclaw` |
| Workspace | `~/.openclaw/workspace` |
| Agent目录 | `~/.openclaw/agents/<agentId>/agent` |
| Sessions | `~/.openclaw/agents/<agentId>/sessions` |

---

## 单代理模式 (默认)

如果不做任何配置，OpenClaw运行单个代理：

- `agentId` 默认为 **`main`**
- Sessions键为 `agent:main:<mainKey>`
- Workspace默认为 `~/.openclaw/workspace`
- 状态默认为 `~/.openclaw/agents/main/agent`

---

## Agent助手

使用代理向导添加新的隔离代理：

```bash
openclaw agents add work
```

然后添加 `bindings` (或让向导做) 来路由入站消息。

验证：

```bash
openclaw agents list --bindings
```

---

## 多代理 = 多人，多人格

使用**多代理**，每个 `agentId` 成为一个**完全隔离的人格**：

- **不同的电话号码/账户** (每个channel `accountId`)
- **不同的人格** (每个代理的workspace文件如 `AGENTS.md` 和 `SOUL.md`)
- **独立的认证 + sessions** (无交叉干扰，除非显式启用)

这让**多人**共享一个Gateway服务器，同时保持AI"大脑"和数据隔离。

---

## 一个WhatsApp号码，多人 (DM分割)

你可以将**不同的WhatsApp DM**路由到不同的代理，同时保持在**一个WhatsApp账户**上。使用 `peer.kind: "direct"` 匹配发送者E.164 (如 `+15551234567`)。回复仍来自同一个WhatsApp号码 (无每个代理的发送者身份)。

重要细节：直接聊天会折叠到代理的**主会话键**，所以真正的隔离需要**每人一个代理**。

示例：

```json5
{
  agents: {
    list: [
      { id: "alex", workspace: "~/.openclaw/workspace-alex" },
      { id: "mia", workspace: "~/.openclaw/workspace-mia" },
    ],
  },
  bindings: [
    {
      agentId: "alex",
      match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551230001" } },
    },
    {
      agentId: "mia",
      match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551230002" } },
    },
  ],
  channels: {
    whatsapp: {
      dmPolicy: "allowlist",
      allowFrom: ["+15551230001", "+15551230002"],
    },
  },
}
```

---

## 路由规则 (消息如何选择代理)

Bindings是**确定性的**，**最具体优先**：

1. `peer` 匹配 (精确 DM/group/channel id)
2. `parentPeer` 匹配 (thread继承)
3. `guildId + roles` (Discord角色路由)
4. `guildId` (Discord)
5. `teamId` (Slack)
6. `accountId` 匹配某个channel
7. channel级别匹配 (`accountId: "*"`)
8. 回退到默认代理 (`agents.list[].default`，否则第一个列表条目，默认: `main`)

如果一个binding设置多个匹配字段 (例如 `peer` + `guildId`)，所有指定字段都是必需的 (`AND` 语义)。

---

## 多账户 / 电话号码

支持**多账户**的channels (如WhatsApp) 使用 `accountId` 标识每次登录。每个 `accountId` 可以路由到不同的代理，这样一个服务器可以托管多个电话号码而不混合sessions。

---

## 概念

- `agentId`: 一个"大脑" (workspace, 每代理认证, 每代理session存储)
- `accountId`: 一个channel账户实例 (如WhatsApp账户 `"personal"` vs `"biz"`)
- `binding`: 通过 `(channel, accountId, peer)` 路由入站消息到 `agentId`，可选guild/team ids
- 直接聊天折叠到 `agent:<agentId>:<mainKey>` (每代理"main"; `session.mainKey`)

---

## 示例：两个WhatsApp → 两个代理

```json5
{
  agents: {
    list: [
      {
        id: "home",
        default: true,
        name: "Home",
        workspace: "~/.openclaw/workspace-home",
        agentDir: "~/.openclaw/agents/home/agent",
      },
      {
        id: "work",
        name: "Work",
        workspace: "~/.openclaw/workspace-work",
        agentDir: "~/.openclaw/agents/work/agent",
      },
    ],
  },

  // 确定性路由：第一个匹配获胜 (最具体的在前)
  bindings: [
    { agentId: "home", match: { channel: "whatsapp", accountId: "personal" } },
    { agentId: "work", match: { channel: "whatsapp", accountId: "biz" } },

    // 可选的每peer覆盖 (示例：发送特定群组到work代理)
    {
      agentId: "work",
      match: {
        channel: "whatsapp",
        accountId: "personal",
        peer: { kind: "group", id: "1203630...@g.us" },
      },
    },
  ],

  tools: {
    agentToAgent: {
      enabled: false,
      allow: ["home", "work"],
    },
  },

  channels: {
    whatsapp: {
      accounts: {
        personal: {},
        biz: {},
      },
    },
  },
}
```

---

## 示例：WhatsApp日常聊天 + Telegram深度工作

按channel分割：将WhatsApp路由到快速日常代理，Telegram路由到Opus代理。

```json5
{
  agents: {
    list: [
      {
        id: "chat",
        name: "Everyday",
        workspace: "~/.openclaw/workspace-chat",
        model: "anthropic/claude-sonnet-4-5",
      },
      {
        id: "opus",
        name: "Deep Work",
        workspace: "~/.openclaw/workspace-opus",
        model: "anthropic/claude-opus-4-6",
      },
    ],
  },
  bindings: [
    { agentId: "chat", match: { channel: "whatsapp" } },
    { agentId: "opus", match: { channel: "telegram" } },
  ],
}
```

---

## 示例：同一channel，一个peer到Opus

保持WhatsApp在快速代理，但将一个DM路由到Opus：

```json5
{
  agents: {
    list: [
      {
        id: "chat",
        name: "Everyday",
        workspace: "~/.openclaw/workspace-chat",
        model: "anthropic/claude-sonnet-4-5",
      },
      {
        id: "opus",
        name: "Deep Work",
        workspace: "~/.openclaw/workspace-opus",
        model: "anthropic/claude-opus-4-6",
      },
    ],
  },
  bindings: [
    {
      agentId: "opus",
      match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551234567" } },
    },
    { agentId: "chat", match: { channel: "whatsapp" } },
  ],
}
```

Peer bindings总是优先，所以将它们保持在channel范围规则之上。

---

## Family代理绑定到WhatsApp群组

将专用family代理绑定到单个WhatsApp群组，带有mention gating和更严格的工具策略：

```json5
{
  agents: {
    list: [
      {
        id: "family",
        name: "Family",
        workspace: "~/.openclaw/workspace-family",
        identity: { name: "Family Bot" },
        groupChat: {
          mentionPatterns: ["@family", "@familybot", "@Family Bot"],
        },
        sandbox: {
          mode: "all",
          scope: "agent",
        },
        tools: {
          allow: [
            "exec",
            "read",
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "sessions_spawn",
            "session_status",
          ],
          deny: ["write", "edit", "apply_patch", "browser", "canvas", "nodes", "cron"],
        },
      },
    ],
  },
  bindings: [
    {
      agentId: "family",
      match: {
        channel: "whatsapp",
        peer: { kind: "group", id: "120363999999999999@g.us" },
      },
    },
  ],
}
```

---

## 每代理Sandbox和工具配置

从v2026.1.6开始，每个代理可以有自己的sandbox和工具限制：

```json5
{
  agents: {
    list: [
      {
        id: "personal",
        workspace: "~/.openclaw/workspace-personal",
        sandbox: {
          mode: "off",  // 个人代理无sandbox
        },
        // 无工具限制 - 所有工具可用
      },
      {
        id: "family",
        workspace: "~/.openclaw/workspace-family",
        sandbox: {
          mode: "all",
          scope: "agent",
          docker: {
            setupCommand: "apt-get update && apt-get install -y git curl",
          },
        },
        tools: {
          allow: ["read"],
          deny: ["exec", "write", "edit", "apply_patch"],
        },
      },
    ],
  },
}
```

**好处：**

- **安全隔离**：为不受信任的代理限制工具
- **资源控制**：sandbox特定代理，同时保持其他在主机上
- **灵活策略**：每个代理不同权限

**注意：** `tools.elevated` 是**全局的**且基于发送者；不可每个代理配置。如果需要每个代理边界，使用 `agents.list[].tools` 来deny `exec`。对于群组目标，使用 `agents.list[].groupChat.mentionPatterns` 以便@mentions干净地映射到预期代理。

---

## 官方参考

- [Multi-Agent Routing](https://docs.openclaw.ai/concepts/multi-agent)
- [Multi-Agent Sandbox & Tools](https://docs.openclaw.ai/tools/multi-agent-sandbox-tools)
- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration-reference)
