# OpenClaw 配置总览

> 官方文档: https://docs.openclaw.ai/gateway/configuration
> 版本: 2026.2.13 | 日期: 2026-02-16

---

## 概述

OpenClaw从 `~/.openclaw/openclaw.json` 读取可选的**JSON5**配置。

如果文件缺失，OpenClaw使用安全默认值。添加配置的常见原因：

- 连接channels并控制谁可以消息bot
- 设置模型、工具、沙箱或自动化 (cron, hooks)
- 调整会话、媒体、网络或UI

---

## 最小配置

```json5
{
  agents: { defaults: { workspace: "~/.openclaw/workspace" } },
  channels: { whatsapp: { allowFrom: ["+15555550123"] } },
}
```

---

## 推荐起始配置

```json5
{
  identity: {
    name: "Clawd",
    theme: "helpful assistant",
    emoji: "🦞",
  },
  agent: {
    workspace: "~/.openclaw/workspace",
    model: { primary: "anthropic/claude-sonnet-4-5" },
  },
  channels: {
    whatsapp: {
      allowFrom: ["+15555550123"],
      groups: { "*": { requireMention: true } },
    },
  },
}
```

---

## 编辑配置

### 交互式向导

```bash
openclaw onboard       # 完整设置向导
openclaw configure     # 配置向导
```

### CLI (单行命令)

```bash
openclaw config get agents.defaults.workspace
openclaw config set agents.defaults.heartbeat.every "2h"
openclaw config unset tools.web.search.apiKey
```

### Control UI

打开 [http://127.0.0.1:18789](http://127.0.0.1:18789) 并使用 **Config** 标签页。

### 直接编辑

直接编辑 `~/.openclaw/openclaw.json`。Gateway监视文件并自动应用更改。

---

## 严格验证

OpenClaw只接受完全匹配schema的配置。未知键、错误类型或无效值会导致Gateway**拒绝启动**。

验证失败时：

- Gateway不启动
- 只有诊断命令有效 (`openclaw doctor`, `openclaw logs`, `openclaw health`, `openclaw status`)
- 运行 `openclaw doctor` 查看具体问题
- 运行 `openclaw doctor --fix` (或 `--yes`) 应用修复

---

## 常见任务

### 设置Channel

每个channel有自己的配置节 `channels.<provider>`:

- [WhatsApp](https://docs.openclaw.ai/channels/whatsapp)
- [Telegram](https://docs.openclaw.ai/channels/telegram)
- [Discord](https://docs.openclaw.ai/channels/discord)
- [Slack](https://docs.openclaw.ai/channels/slack)
- [Signal](https://docs.openclaw.ai/channels/signal)
- [iMessage](https://docs.openclaw.ai/channels/imessage)
- [Google Chat](https://docs.openclaw.ai/channels/googlechat)
- [Mattermost](https://docs.openclaw.ai/channels/mattermost)
- [MS Teams](https://docs.openclaw.ai/channels/msteams)

**DM策略模式:**

```json5
{
  channels: {
    telegram: {
      enabled: true,
      botToken: "123:abc",
      dmPolicy: "pairing",
      allowFrom: ["tg:123"],
    },
  },
}
```

### 选择和配置模型

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "anthropic/claude-sonnet-4-5",
        fallbacks: ["openai/gpt-5.2"],
      },
      models: {
        "anthropic/claude-sonnet-4-5": { alias: "Sonnet" },
        "openai/gpt-5.2": { alias: "GPT" },
      },
    },
  },
}
```

### 控制谁可以消息bot

**DM策略:**

| 策略 | 描述 |
|------|------|
| `pairing` (默认) | 未知发送者获得一次性配对码 |
| `allowlist` | 只有白名单中的发送者 |
| `open` | 允许所有入站DM (需要 `allowFrom: ["*"]`) |
| `disabled` | 忽略所有DM |

### 群聊Mention Gating

```json5
{
  agents: {
    list: [
      {
        id: "main",
        groupChat: {
          mentionPatterns: ["@openclaw", "openclaw"],
        },
      },
    ],
  },
  channels: {
    whatsapp: {
      groups: { "*": { requireMention: true } },
    },
  },
}
```

### 配置会话和重置

```json5
{
  session: {
    dmScope: "per-channel-peer",
    reset: {
      mode: "daily",
      atHour: 4,
      idleMinutes: 120,
    },
  },
}
```

**dmScope选项:**

| 值 | 说明 |
|----|------|
| `main` | 所有DM共享主会话 |
| `per-peer` | 按发送者ID跨channel隔离 |
| `per-channel-peer` | 按channel+发送者隔离 (推荐多用户) |
| `per-account-channel-peer` | 按账户+channel+发送者隔离 (推荐多账户) |

### 启用沙箱

```json5
{
  agents: {
    defaults: {
      sandbox: {
        mode: "non-main",
        scope: "agent",
      },
    },
  },
}
```

### 设置Heartbeat

```json5
{
  agents: {
    defaults: {
      heartbeat: {
        every: "30m",
        target: "last",
      },
    },
  },
}
```

### 配置Cron Jobs

```json5
{
  cron: {
    enabled: true,
    maxConcurrentRuns: 2,
    sessionRetention: "24h",
  },
}
```

### 配置多代理路由

```json5
{
  agents: {
    list: [
      { id: "home", default: true, workspace: "~/.openclaw/workspace-home" },
      { id: "work", workspace: "~/.openclaw/workspace-work" },
    ],
  },
  bindings: [
    { agentId: "home", match: { channel: "whatsapp", accountId: "personal" } },
    { agentId: "work", match: { channel: "whatsapp", accountId: "biz" } },
  ],
}
```

### 分割配置到多个文件 ($include)

```json5
{
  gateway: { port: 18789 },
  agents: { $include: "./agents.json5" },
  broadcast: {
    $include: ["./clients/a.json5", "./clients/b.json5"],
  },
}
```

---

## 配置热重载

Gateway监视 `~/.openclaw/openclaw.json` 并自动应用更改 — 大多数设置无需手动重启。

### 重载模式

| 模式 | 行为 |
|------|------|
| `hybrid` (默认) | 立即热应用安全更改。自动重启关键更改。 |
| `hot` | 只热应用安全更改。需要重启时记录警告。 |
| `restart` | 任何配置更改都重启Gateway。 |
| `off` | 禁用文件监视。手动重启生效。 |

```json5
{
  gateway: {
    reload: { mode: "hybrid", debounceMs: 300 },
  },
}
```

### 什么热应用 vs 什么需要重启

| 类别 | 字段 | 需要重启? |
|------|------|-----------|
| Channels | `channels.*`, `web` | 否 |
| Agent & models | `agent`, `agents`, `models`, `routing` | 否 |
| Automation | `hooks`, `cron`, `agent.heartbeat` | 否 |
| Sessions & messages | `session`, `messages` | 否 |
| Tools & media | `tools`, `browser`, `skills`, `audio`, `talk` | 否 |
| UI & misc | `ui`, `logging`, `identity`, `bindings` | 否 |
| Gateway server | `gateway.*` (port, bind, auth, tailscale, TLS, HTTP) | **是** |
| Infrastructure | `discovery`, `canvasHost`, `plugins` | **是** |

---

## 官方参考

- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration-reference) - 完整字段参考
- [Configuration Examples](https://docs.openclaw.ai/gateway/configuration-examples) - 配置示例
- [Multi-Agent](https://docs.openclaw.ai/concepts/multi-agent) - 多代理路由
