# OPS-LINEAR-009 回滚计划

> 文档编号：OPS-LINEAR-009  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker

---

## 一、方案摘要

本方案定义 AEdu Linear 自动化运营系统的回滚策略，用于在 canary label 部署失败或验证不通过时，快速回退到 OPS-008 基线版本或执行 dry-run 回滚验证。

**核心目标**：一条命令完成回滚，最小化故障影响窗口，保证数据库连接安全保留。

---

## 二、回滚触发条件

| 场景 | 触发条件 | 回滚级别 |
|------|---------|---------|
| Canary 标签验证失败 | 新部署 canary 阶段错误率 >5% 或 health check 失败 | 全量回滚 |
| Linear Webhook 端到端超时 | 端到端延迟 >10s 持续 5 分钟 | 服务回滚 |
| n8n 工作流异常 | workflow 失败率 >50% 且不可自愈 | 服务回滚 |
| 数据入库异常 | 事件丢失率 >1% 或 schema 不兼容 | 数据回滚 + 服务回滚 |

---

## 三、一键回滚命令

### 3.1 标准回滚命令

```bash
make rollback ENV=<environment>
```

**说明**：
- `ENV`：目标环境（dev / staging / prod）
- 回滚到上一个稳定版本（由 `.last-stable-version` 文件记录）

### 3.2 Dry-run 回滚验证

在正式回滚前，必须先执行 dry-run 验证回滚路径：

```bash
make rollback-dryrun ENV=<environment>
```

**Dry-run 执行内容**：
1. 验证目标版本镜像/代码可用性
2. 检查数据库连接可达性
3. 检查回滚脚本权限
4. 输出回滚影响评估报告
5. **不执行任何实际变更**

### 3.3 Makefile 回滚目标定义

```makefile
.PHONY: rollback rollback-dryrun

rollback:
	@if [ -z "$(ENV)" ]; then \
		echo "ERROR: ENV is required. Usage: make rollback ENV=<environment>"; \
		exit 1; \
	fi
	@if [ ! -f deploy/$(ENV)/.last-stable-version ]; then \
		echo "ERROR: No stable version recorded for $(ENV)"; \
		exit 1; \
	fi
	@echo "Starting rollback for $(ENV) environment..."
	@export DB_URL=$$(cat deploy/$(ENV)/.db-url 2>/dev/null || echo ""); \
	if [ -z "$$DB_URL" ]; then \
		echo "ERROR: DB_URL not preserved in deploy/$(ENV)/.db-url"; \
		exit 1; \
	fi; \
	echo "DB_URL preserved: OK"; \
	DEPLOY_TARGET=$$(cat deploy/$(ENV)/.last-stable-version) && \
	./scripts/rollback.sh --env $(ENV) --target $$DEPLOY_TARGET --db-url "$$DB_URL"

rollback-dryrun:
	@if [ -z "$(ENV)" ]; then \
		echo "ERROR: ENV is required. Usage: make rollback-dryrun ENV=<environment>"; \
		exit 1; \
	fi
	@echo "Starting DRY-RUN rollback validation for $(ENV) environment..."
	@./scripts/rollback.sh --env $(ENV) --dryrun --check-only
```

---

## 四、回滚脚本核心逻辑

### 4.1 rollback.sh 核心流程

```bash
#!/bin/bash
# rollback.sh - AEdu Linear 运营系统回滚脚本

set -euo pipefail

# 参数解析
ENV=""
TARGET=""
DRYRUN=false
CHECK_ONLY=false
DB_URL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --env) ENV="$2"; shift 2;;
        --target) TARGET="$2"; shift 2;;
        --dryrun) DRYRUN=true; shift;;
        --check-only) CHECK_ONLY=true; shift;;
        --db-url) DB_URL="$2"; shift 2;;
        *) echo "Unknown option: $1"; exit 1;;
    esac
done

# 前置检查
pre_check() {
    echo "[CHECK] Validating rollback prerequisites..."
    
    # 1. 检查目标版本可用性
    if ! image_exists "$TARGET"; then
        echo "[FAIL] Target version $TARGET not found in registry"
        exit 1
    fi
    echo "[OK] Target version $TARGET available"
    
    # 2. 检查数据库连接（如提供）
    if [ -n "$DB_URL" ]; then
        if ! test_db_connection "$DB_URL"; then
            echo "[WARN] Database connection test failed"
            if [ "$CHECK_ONLY" = true ]; then
                exit 1
            fi
        else
            echo "[OK] Database connection verified"
        fi
    fi
    
    # 3. 检查回滚脚本权限
    if [ ! -x "scripts/rollback.sh" ]; then
        echo "[FAIL] rollback.sh not executable"
        exit 1
    fi
    echo "[OK] Script permissions valid"
}

# 执行回滚（仅非 dry-run 模式）
execute_rollback() {
    if [ "$DRYRUN" = true ] || [ "$CHECK_ONLY" = true ]; then
        echo "[DRY-RUN] Would rollback to version: $TARGET"
        echo "[DRY-RUN] Environment: $ENV"
        echo "[DRY-RUN] DB_URL preserved: ${DB_URL:+YES}"
        return 0
    fi
    
    echo "[EXEC] Rolling back $ENV to $TARGET..."
    
    # 保存当前版本作为下次回滚目标
    current_version=$(get_current_version "$ENV")
    echo "$current_version" > "deploy/${ENV}/.last-stable-version"
    
    # 执行实际回滚
    deploy_version "$ENV" "$TARGET"
    
    echo "[SUCCESS] Rollback complete for $ENV"
}

# 主流程
pre_check
execute_rollback
```

---

## 五、DB_URL 保留策略

### 5.1 保留原则

**DB_URL 在任何回滚操作中必须保持不变**，禁止在回滚过程中重新生成或覆盖数据库连接字符串。

### 5.2 保留机制

| 机制 | 说明 | 位置 |
|------|------|------|
| 本地文件缓存 | 部署时将 DB_URL 写入环境专属文件 | `deploy/<env>/.db-url` |
| 环境变量 | 回滚脚本从环境变量或文件读取 | `ROLLBACK_DB_URL` 环境变量 |
| 密钥管理 | 生产环境使用密钥管理服务 | Vault / Secrets Manager |

### 5.3 文件权限

```bash
# .db-url 文件权限设置
chmod 600 deploy/*/ .db-url
chown deploy-user:deploy-group deploy/*/ .db-url
```

### 5.4 回滚前验证

```bash
# 验证 DB_URL 可用性
verify_db_url() {
    local db_url="${1:-}"
    if [ -z "$db_url" ]; then
        echo "[FAIL] DB_URL is empty"
        return 1
    fi
    # 测试连接（只测试，不修改）
    if ! timeout 5 bash -c "echo 'SELECT 1' | psql \"$db_url\" > /dev/null 2>&1"; then
        echo "[WARN] DB_URL connection test failed, but proceeding (may be network issue)"
        return 0
    fi
    echo "[OK] DB_URL connection verified"
}
```

---

## 六、可选：禁用动作环境变量

### 6.1 使用场景

当需要临时禁用特定动作（如 Linear Webhook 转发、n8n 工作流执行）而不回滚整个服务时，可通过环境变量控制：

| 环境变量 | 作用 | 默认值 |
|---------|------|--------|
| `DISABLE_LINEAR_WEBHOOK` | 禁用 Linear Webhook 接收 | `false` |
| `DISABLE_N8N_WORKFLOW` | 禁用 n8n 工作流执行 | `false` |
| `DISABLE_EVENT_INGESTION` | 禁用事件入库 | `false` |
| `READ_ONLY_MODE` | 只读模式（允许查询，禁止写入） | `false` |

### 6.2 快速禁用命令

```bash
# 临时禁用 Linear Webhook（不停止服务）
kubectl set env deployment/gateway-admin -n aedu DISABLE_LINEAR_WEBHOOK=true

# 恢复
kubectl set env deployment/gateway-admin -n aedu DISABLE_LINEAR_WEBHOOK=false

# 全局只读模式
kubectl set env deployment/gateway-admin -n aedu READ_ONLY_MODE=true
```

---

## 七、回滚后验证

### 7.1 自动验证项

回滚完成后自动执行以下检查：

| 检查项 | 命令 | 预期结果 |
|--------|------|---------|
| 服务健康 | `curl https://<n8n域名>/healthz` | HTTP 200 |
| Webhook 接收 | 发送测试事件 | 200 OK |
| 数据库连接 | 执行简单查询 | 连接成功 |
| 版本确认 | `kubectl get deploy -n aedu -o jsonpath='{.spec.template.spec.containers[0].image}'` | 镜像版本匹配目标版本 |

### 7.2 手动验证项

- [ ] Linear UI 中 Webhook 状态为 active
- [ ] 事件面板可访问且显示正常
- [ ] 最近 5 分钟无错误告警
- [ ] 日志中无异常堆栈

---

## 八、回滚影响评估

### 8.1 影响范围

| 组件 | 回滚影响 | 恢复时间 |
|------|---------|---------|
| gateway-admin | 短暂中断（<30s） | 立即 |
| n8n | 短暂中断（<60s） | 立即 |
| 事件面板 | 短暂不可用 | 服务恢复后可用 |
| 数据库 | **不受影响**（DB_URL 保留） | 无影响 |
| Linear Webhook | 回滚期间事件可能丢失 | 依赖 Linear 重试机制 |

### 8.2 数据安全保障

| 保障措施 | 说明 |
|---------|------|
| DB_URL 不变 | 数据库连接字符串在回滚全程保持不变 |
| 只读验证 | Dry-run 模式不执行任何写入操作 |
| 事件缓冲 | 回滚期间 Linear Webhook 事件由 Linear 侧缓冲重试 |
| 审计日志 | 回滚操作本身记录到审计日志 |

---

## 九、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-009 回滚计划 | OPS-008 试点阶段问题库 | 回滚触发场景应记录到问题库 |
| OPS-LINEAR-009 回滚计划 | OPS-LINEAR-002 验收清单 | 回滚后验证对齐 P0 验收标准 |
| OPS-LINEAR-009 回滚计划 | ARCH-012 部署交付与运维方案 | 回滚机制遵循部署运维方案的故障处理流程 |
| OPS-LINEAR-009 回滚计划 | GRAPH-009 图谱写入与版本回滚 | 参考图谱版本回滚的设计原则 |

---

## 十、执行 Checklist

### 回滚前
- [ ] 确认回滚触发原因并记录
- [ ] 执行 `make rollback-dryrun ENV=<env>` 验证回滚路径
- [ ] 确认 DB_URL 文件存在且可读
- [ ] 通知相关团队成员

### 回滚中
- [ ] 执行 `make rollback ENV=<env>`
- [ ] 监控回滚进度和日志
- [ ] 确认服务版本已切换

### 回滚后
- [ ] 执行自动验证项
- [ ] 执行手动验证项
- [ ] 确认 Linear Webhook 重新 active
- [ ] 记录回滚操作到审计日志
- [ ] 在 OPS-008 问题库中登记回滚事件

---

**文档状态**：草稿中  
**审批人**：待定  
**下次评审日期**：待定
