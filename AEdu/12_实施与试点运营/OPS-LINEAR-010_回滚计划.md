# OPS-LINEAR-010 回滚计划

> 文档编号：OPS-LINEAR-010  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  
> 状态：草稿中  
> 用途：定义 OPS-010（TWIN）部署后回滚到 OPS-009（KB+INGEST）label-scope canary 的具体方案

---

## 一、方案摘要

本方案专门定义 **OPS-010（TWIN 试点）部署后，快速回滚到 OPS-009（KB+INGEST）label-scope canary 基线** 的回滚策略。

**核心目标**：
1. 一条命令完成 label-scope 的 env/config/image 回滚
2. 保留 dry-run 紧急降级路径
3. 回滚后系统状态等同于 OPS-009 canary 部署完成后的状态

---

## 二、回滚目标与场景

### 2.1 回滚目标

| 项目 | 回滚前 | 回滚后 |
|------|--------|--------|
| Label Scope | OPS-010（TWIN 范围） | OPS-009（KB+INGEST 范围） |
| Canary 配置 | TWIN 试点配置 | KB+INGEST 试点配置 |
| 镜像版本 | TWIN 相关镜像 | KB+INGEST 基线镜像 |
| 环境变量 | TWIN 新增变量 | 移除 TWIN 变量，恢复 OPS-009 变量 |

### 2.2 触发条件

| 场景 | 触发条件 | 严重级别 |
|------|---------|---------|
| TWIN 状态更新异常 | 状态分流错误率 >5% | P0 - 立即回滚 |
| KB+INGEST 消费链路中断 | TWIN 消费导致 INGEST 事件丢失 | P0 - 立即回滚 |
| 人工复核池异常堆积 | TWIN 产生大量 `review_needed` 事件 | P1 - 评估后回滚 |
| 边界冲突 | TWIN 越权修改 KB/GRAPH 数据 | P0 - 立即回滚 |

---

## 三、一键回滚命令

### 3.1 标准回滚命令

```bash
make rollback-to-ops009 ENV=<environment>
```

**参数说明**：
- `ENV`：目标环境（dev / staging / prod）
- 回滚到 OPS-009 canary 基线配置

### 3.2 Dry-run 紧急降级

```bash
make rollback-to-ops009-dryrun ENV=<environment>
```

**Dry-run 执行内容**：
1. 验证 OPS-009 基线配置可用性
2. 检查 label-scope 当前状态
3. 输出回滚影响评估
4. **不执行任何实际变更**

---

## 四、Makefile 目标定义

```makefile
.PHONY: rollback-to-ops009 rollback-to-ops009-dryrun

# 回滚到 OPS-009 label-scope canary 基线
rollback-to-ops009:
	@if [ -z "$(ENV)" ]; then \
		echo "ERROR: ENV is required. Usage: make rollback-to-ops009 ENV=<environment>"; \
		exit 1; \
	fi
	@echo "=== Rollback to OPS-009 label-scope canary ==="
	@echo "Environment: $(ENV)"
	@echo "Target: KB+INGEST pilot scope (OPS-009)"
	@echo ""
	@# 1. 保存当前 OPS-010 配置快照
	@echo "[1/4] Saving current OPS-010 config snapshot..."
	@mkdir -p deploy/$(ENV)/snapshots
	@kubectl get configmap -n aedu -l scope=label-scope -o yaml > deploy/$(ENV)/snapshots/ops010-config-$$(date +%Y%m%d%H%M%S).yaml 2>/dev/null || echo "  [WARN] No existing configmap to snapshot"
	@# 2. 恢复 OPS-009 label-scope 环境变量
	@echo "[2/4] Restoring OPS-009 env variables..."
	@kubectl set env deployment/gateway-admin -n aedu \
		--from-file=deploy/$(ENV)/ops009-env-config 2>/dev/null || echo "  [WARN] Using inline env restore"
	@# 3. 切换镜像到 OPS-009 基线
	@echo "[3/4] Switching image to OPS-009 baseline..."
	@kubectl set image deployment/gateway-admin -n aedu \
		gateway-admin=$$(cat deploy/$(ENV)/.ops009-image-tag) 2>/dev/null || echo "  [WARN] Image switch skipped"
	@# 4. 验证回滚结果
	@echo "[4/4] Verifying rollback..."
	@sleep 10
	@kubectl rollout status deployment/gateway-admin -n aedu --timeout=120s
	@echo ""
	@echo "=== Rollback complete ==="
	@echo "Label scope: OPS-009 (KB+INGEST)"
	@echo "Verify: curl https://<gateway>/healthz"

# Dry-run 验证回滚路径
rollback-to-ops009-dryrun:
	@if [ -z "$(ENV)" ]; then \
		echo "ERROR: ENV is required. Usage: make rollback-to-ops009-dryrun ENV=<environment>"; \
		exit 1; \
	fi
	@echo "=== DRY-RUN: Rollback to OPS-009 label-scope canary ==="
	@echo "Environment: $(ENV)"
	@echo ""
	@echo "[CHECK] Current label-scope configuration:"
	@kubectl get configmap -n aedu -l scope=label-scope 2>/dev/null || echo "  [INFO] No label-scope configmap found"
	@echo ""
	@echo "[CHECK] Current image:"
	@kubectl get deployment gateway-admin -n aedu -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "  [INFO] Deployment not found"
	@echo ""
	@echo "[CHECK] OPS-009 baseline image:"
	@cat deploy/$(ENV)/.ops009-image-tag 2>/dev/null || echo "  [WARN] OPS-009 image tag not recorded"
	@echo ""
	@echo "[CHECK] OPS-009 env config:"
	@cat deploy/$(ENV)/ops009-env-config 2>/dev/null || echo "  [WARN] OPS-009 env config not found"
	@echo ""
	@echo "[DRY-RUN] Would execute:"
	@echo "  1. kubectl set env ... (restore OPS-009 variables)"
	@echo "  2. kubectl set image ... (switch to OPS-009 baseline)"
	@echo "  3. kubectl rollout status ... (verify)"
	@echo ""
	@echo "=== DRY-RUN complete ==="
```

---

## 五、回滚前置检查清单

### 5.1 回滚前必须确认

- [ ] OPS-009 基线镜像 tag 已记录在 `deploy/<env>/.ops009-image-tag`
- [ ] OPS-009 环境变量配置已保存在 `deploy/<env>/ops009-env-config`
- [ ] Label-scope canary 当前状态已记录
- [ ] 回滚触发原因已记录到 OPS-008 问题库

### 5.2 关键文件位置

| 文件 | 用途 | 必需性 |
|------|------|--------|
| `deploy/<env>/.ops009-image-tag` | OPS-009 基线镜像 tag | 必需 |
| `deploy/<env>/ops009-env-config` | OPS-009 环境变量配置 | 必需 |
| `deploy/<env>/snapshots/` | 回滚前配置快照 | 推荐 |
| `deploy/<env>/.last-stable-version` | 最后稳定版本记录 | 推荐 |

---

## 六、紧急降级路径

### 6.1 当一键回滚不可用时的紧急降级

如果 `make rollback-to-ops009` 命令执行失败或环境异常，执行以下手动步骤：

```bash
# 步骤 1：手动恢复环境变量
kubectl set env deployment/gateway-admin -n aedu \
  SCOPE_LABEL=kb_ingest \
  PILOT_MODE=ops009 \
  TWIN_ENABLED=false

# 步骤 2：手动切换镜像（如果记录了 tag）
kubectl set image deployment/gateway-admin -n aedu \
  gateway-admin=<ops009-image-tag>

# 步骤 3：等待滚动更新完成
kubectl rollout status deployment/gateway-admin -n aedu --timeout=120s

# 步骤 4：验证服务健康
curl -s https://<gateway>/healthz | grep -q "ok" && echo "OK" || echo "FAIL"
```

### 6.2 当 kubectl 不可用时的兜底方案

如果集群访问异常，通过以下方式降级：

1. **功能开关降级**：通过环境变量禁用 TWIN 功能
2. **流量切换降级**：通过 Ingress/网关将流量切回 OPS-009 端点
3. **DNS 降级**：修改 DNS 指向 OPS-009 基线服务

---

## 七、回滚后验证

### 7.1 自动验证

| 检查项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| Label Scope | `kubectl get cm -n aedu -l scope=label-scope` | scope=kb_ingest |
| 服务健康 | `curl /healthz` | HTTP 200 |
| 镜像版本 | `kubectl get deploy -o jsonpath` | 匹配 OPS-009 tag |
| 事件流 | 发送测试事件 | KB+INGEST 正常处理 |
| TWIN 消费 | 检查 TWIN 消费开关 | TWIN 消费已关闭 |

### 7.2 手动验证

- [ ] KB 查询接口正常响应
- [ ] INGEST 事件生成链路正常
- [ ] OPS-009 范围内的功能正常
- [ ] 最近 5 分钟无新增错误
- [ ] 人工复核池无异常堆积

---

## 八、注意事项

### 8.1 数据一致性

- 回滚后，TWIN 产生的状态更新**不应被自动清除**
- 如需清理 TWIN 状态，需单独执行数据清理脚本
- KB+INGEST 产生的事件数据**不受回滚影响**

### 8.2 与 OPS-LINEAR-009 的关系

- OPS-LINEAR-009 是通用回滚计划，适用于所有 canary 部署
- OPS-LINEAR-010 是专用回滚计划，专门针对 OPS-010→OPS-009 的场景
- 两者可配合使用：先用 OPS-LINEAR-010 快速回滚，再用 OPS-LINEAR-009 做深度回滚验证

### 8.3 灰度回滚选项

如需逐步回滚而非全量回滚：

```bash
# 先回滚 50% 流量
kubectl set env deployment/gateway-admin -n aedu TWIN_TRAFFIC_WEIGHT=0.5

# 观察 10 分钟后，如无问题则全量回滚
kubectl set env deployment/gateway-admin -n aedu TWIN_TRAFFIC_WEIGHT=0
```

---

## 九、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-010 回滚计划 | OPS-LINEAR-009 回滚计划 | 通用回滚基础上的专用回滚方案 |
| OPS-LINEAR-010 回滚计划 | OPS-009 KB+INGEST 试点范围 | 回滚目标为该文档定义的范围 |
| OPS-LINEAR-010 回滚计划 | OPS-010 TWIN 试点范围 | 回滚源为该文档定义的范围 |
| OPS-LINEAR-010 回滚计划 | ARCH-012 部署交付与运维方案 | 回滚机制遵循部署运维方案 |
| OPS-LINEAR-010 回滚计划 | ARCH-011 测试验收与灰度发布标准 | 回滚验证对齐灰度发布标准 |

---

## 十、执行 Checklist

### 回滚前
- [ ] 确认回滚触发原因（记录到 OPS-008）
- [ ] 执行 `make rollback-to-ops009-dryrun ENV=<env>`
- [ ] 确认 OPS-009 基线文件存在（image tag + env config）
- [ ] 通知相关团队成员

### 回滚中
- [ ] 执行 `make rollback-to-ops009 ENV=<env>`
- [ ] 监控滚动更新进度
- [ ] 确认 label-scope 已切换到 OPS-009

### 回滚后
- [ ] 执行自动验证项
- [ ] 执行手动验证项
- [ ] 确认 KB+INGEST 功能正常
- [ ] 确认 TWIN 功能已关闭
- [ ] 记录回滚操作到审计日志

---

**文档状态**：草稿中  
**审批人**：待定  
**下次评审日期**：待定
