### BOOT.md
每次 Gateway 启动时，请严格执行以下原子化指令：
1. 调用 `sessions_send` 工具，参数：{ "sessionKey": "main", "text": "⚡ 主权模式启动成功。Molt (18789) 已就绪，包年 GLM 能源已并网。" }
2. 指令执行完毕后，回复 NO_REPLY，随后保持静默。
