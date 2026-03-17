# 🛡️ 系统监控清单 (V5.2 - 主权本地版)

1. **本地数据库检查**：
   - 执行连接测试（如 `pg_isready` 或轻量级查询），确保本地数据源（Postgres/SQLite）响应在 200ms 内。
   - 验证数据目录读写权限，确保索引文件未被锁定。
   - ⚠️ **优先级最高**：若本地库阻塞，视为领土记忆丧失，立即熔断所有写操作。

2. **Git 完整性**：
   - 执行 `git status --porcelain`，检查是否有未提交的逻辑污染。
   - 严禁在”脏代码”状态下执行生产部署，保持逻辑纯净度。

3. **日志清理**：
   - 监控 `/Users/busiji/passkills/logs/` 总体积。
   - 若文件夹超过 **100MB**，自动触发 `logrotate` 压缩逻辑，防止物理空间溢出。

4. **文件结构检查**：
   - 检查根目录 `/Users/busiji/passkills/` 是否存在冗余的核心文件
   - 核心文件包括：AGENTS.md, SOUL.md, IDENTITY.md, USER.md, TOOLS.md, HEARTBEAT.md, MEMORY.md
   - 若发现冗余文件，立即报警并删除
   - 所有核心文件应该只存在于 `/Users/busiji/passkills/workspace/` 目录下

---

**📜 执行准则**：
- 若上述检查全部通过，回复 `HEARTBEAT_OK` 保持静默守护。
- 若有任何阻塞或延迟异常，立即通过紧急通道报警，并输出完整的故障堆栈。