# 救援机器人操作基线文档

> 版本: 1.0 | 日期: 2026-02-16 | 状态: 草案

---

## 1. 概述

### 1.1 定义
**救援机器人 (Rescue Robot)** — 当主AI系统出现故障、响应异常或服务中断时，能够自动或手动介入执行关键任务的备份系统。

### 1.2 核心原则
- **幂等性**: 重复执行不会造成额外损害
- **最小权限**: 只授予救援所需的最小权限
- **可观测性**: 所有操作可追溯、可审计
- **快速恢复**: 从检测到介入 < 30秒

---

## 2. 系统架构

### 2.1 组件拓扑

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                            │
│              (Webchat / Telegram / Signal)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   主 AI 会话 (Main)                      │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Gateway   │◄──►│   Agent     │◄──►│   Tools     │ │
│  │   (路由)    │    │   (核心)    │    │   (工具)    │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                   │                          │
│         │    ┌──────────────┴──────────────┐          │
│         │    │      健康检查器              │          │
│         │    │   (Health Monitor)          │          │
│         │    └──────────────┬──────────────┘          │
│         │                   │                          │
└─────────┼───────────────────┼──────────────────────────┘
          │                   │
          │    ┌──────────────▼──────────────┐
          │    │                              │
          │    │      救援机器人              │
          │    │    (Rescue Agent)           │
          │    │                              │
          │    │  - 心跳检测                  │
          │    │  - 故障判定                  │
          │    │  - 自动接管                  │
          │    │  - 降级服务                  │
          │    │                              │
          │    └──────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                    外部服务层                            │
│         (API / Database / File Storage)                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 救援机器人类型

| 类型 | 触发条件 | 权限级别 | 示例用途 |
|------|----------|----------|----------|
| **监控型** | 周期性心跳超时 | 只读 | 状态报告、告警 |
| **通知型** | 主服务无响应 | 发送消息 | 通知管理员、用户 |
| **执行型** | 明确故障信号 | 受限执行 | 重启服务、回滚配置 |
| **接管型** | 主服务完全失效 | 完整权限 | 降级服务、紧急处理 |

---

## 3. 操作流程

### 3.1 正常心跳流程

```
┌─────────┐     心跳请求      ┌─────────────┐
│  Main   │ ───────────────► │   Rescue    │
│ Agent   │                  │   Robot     │
│         │ ◄─────────────── │             │
└─────────┘    心跳响应(OK)   └─────────────┘
    │
    │  每 30-60 秒
    │
    ▼
  继续
```

### 3.2 故障检测与介入

```
时间线:
────────────────────────────────────────────────────────────►

T+0s     T+30s      T+60s       T+90s        T+120s
  │        │          │           │             │
  ▼        ▼          ▼           ▼             ▼
正常    心跳超时#1   心跳超时#2   心跳超时#3    触发救援
                      │                          │
                      ▼                          ▼
                   发送警告                   执行救援协议
                   (可能延迟)               (降级/通知/重启)
```

### 3.3 救援协议 (Rescue Protocol)

#### Phase 1: 检测 (Detection)
```yaml
trigger_conditions:
  - heartbeat_timeout: 90s      # 3次心跳丢失
  - explicit_signal: "RESCUE"   # 手动触发
  - error_rate: ">50%"          # 错误率超限
  - memory_leak: ">90%"         # 资源耗尽
```

#### Phase 2: 诊断 (Diagnosis)
```yaml
diagnostic_checks:
  - service_status: "openclaw gateway status"
  - process_alive: "pgrep -f openclaw"
  - port_binding: "lsof -i :3000"
  - disk_space: "df -h"
  - recent_logs: "tail -100 ~/.openclaw/logs/gateway.log"
```

#### Phase 3: 介入 (Intervention)
```yaml
intervention_actions:
  level_1_notify:
    - log_incident
    - notify_admin(message: "Main agent unresponsive")
    - update_status_page(status: "degraded")
  
  level_2_restart:
    - safe_shutdown(timeout: 10s)
    - restart_service: "openclaw gateway restart"
    - verify_recovery
    - notify_recovery
  
  level_3_escalate:
    - escalate_to_human
    - enable_manual_mode
    - preserve_state_for_debug
```

#### Phase 4: 恢复 (Recovery)
```yaml
recovery_steps:
  - verify_main_agent_healthy
  - sync_state_from_rescue
  - resume_normal_operations
  - generate_incident_report
  - update_runbook
```

---

## 4. 配置规范

### 4.1 救援机器人配置文件

```json
{
  "rescueRobot": {
    "enabled": true,
    "agentId": "rescue-agent",
    "model": "zai/glm-5",
    "thinking": "low",
    
    "monitoring": {
      "heartbeatIntervalMs": 30000,
      "timeoutThreshold": 3,
      "diagnosticIntervalMs": 10000
    },
    
    "triggers": {
      "heartbeatTimeout": true,
      "errorRate": 0.5,
      "memoryThreshold": 0.9,
      "manualKeyword": "RESCUE"
    },
    
    "actions": {
      "notify": {
        "channels": ["telegram", "email"],
        "recipients": ["admin@example.com"]
      },
      "restart": {
        "enabled": true,
        "maxAttempts": 3,
        "cooldownMs": 60000
      },
      "escalate": {
        "timeoutMs": 300000,
        "fallbackHuman": "on-call-engineer"
      }
    },
    
    "safety": {
      "maxActionsPerHour": 5,
      "requireConfirmation": ["restart", "delete", "modify_config"],
      "dryRunDefault": true
    }
  }
}
```

### 4.2 Cron 任务配置 (心跳检测)

```yaml
# 救援心跳检测 - 每2分钟
- job_id: rescue-heartbeat-check
  schedule: "*/2 * * * *"
  sessionTarget: isolated
  payload:
    kind: agentTurn
    message: |
      执行救援机器人心跳检查。
      1. 检查主会话状态
      2. 如果上次心跳超过90秒，发送告警
      3. 如果超过3次失败，执行救援协议
    thinking: low
```

---

## 5. 命令接口

### 5.1 手动触发命令

```bash
# 查看救援机器人状态
openclaw rescue status

# 手动触发救援
openclaw rescue trigger --reason "manual intervention"

# 取消救援状态
openclaw rescue cancel

# 查看救援历史
openclaw rescue history --last 24h
```

### 5.2 消息触发 (通过聊天)

```
用户: /rescue status
用户: /rescue trigger
用户: /rescue cancel
```

---

## 6. 安全考虑

### 6.1 权限分离

| 操作 | Main Agent | Rescue Robot |
|------|------------|--------------|
| 读取文件 | ✅ | ✅ |
| 发送消息 | ✅ | ✅ (受限) |
| 修改配置 | ✅ | ❌ (需确认) |
| 执行命令 | ✅ | ❌ (白名单) |
| 删除数据 | ✅ | ❌ |

### 6.2 防止救援机器人失控

```yaml
failsafe:
  # 救援机器人自身也需要被监控
  self_monitoring: true
  
  # 限制操作频率
  rate_limit:
    max_actions_per_minute: 2
    max_actions_per_hour: 10
  
  # 关键操作需要二次确认
  destructive_actions:
    - delete_files
    - modify_config
    - restart_service
    require:
      - human_confirmation
      - two_factor_auth  # 可选
  
  # 紧急熔断
  circuit_breaker:
    trigger: "rescue_robot_error_rate > 80%"
    action: "disable_rescue_robot, notify_admin"
```

---

## 7. 监控与告警

### 7.1 监控指标

```yaml
metrics:
  - name: rescue_heartbeat_latency
    type: gauge
    description: "心跳响应延迟"
    alert_threshold: ">30s"
  
  - name: rescue_trigger_count
    type: counter
    description: "救援触发次数"
    alert_threshold: ">3/hour"
  
  - name: rescue_recovery_time
    type: histogram
    description: "恢复耗时"
    target: "<60s"
  
  - name: main_agent_uptime
    type: gauge
    description: "主代理可用性"
    target: ">99.9%"
```

### 7.2 告警规则

```yaml
alerts:
  - name: MainAgentDown
    condition: "no_heartbeat > 90s"
    severity: critical
    actions:
      - trigger_rescue
      - page_on_call
  
  - name: RescueRobotTriggered
    condition: "rescue_triggered == true"
    severity: warning
    actions:
      - notify_admin
  
  - name: RescueRobotFailed
    condition: "rescue_action_failed == true"
    severity: critical
    actions:
      - page_on_call
      - escalate_to_human
```

---

## 8. 事件日志格式

### 8.1 标准日志结构

```json
{
  "timestamp": "2026-02-16T09:18:00+08:00",
  "event_type": "rescue_triggered",
  "source": "rescue-robot",
  "severity": "warning",
  "details": {
    "trigger_reason": "heartbeat_timeout",
    "last_healthy_heartbeat": "2026-02-16T09:16:30+08:00",
    "consecutive_failures": 3,
    "diagnostic_data": {
      "service_status": "running",
      "memory_usage": "45%",
      "error_rate": "0%"
    }
  },
  "actions_taken": [
    {
      "action": "notify_admin",
      "status": "success",
      "timestamp": "2026-02-16T09:18:01+08:00"
    }
  ]
}
```

---

## 9. 故障场景与响应

### 9.1 场景矩阵

| 场景 | 检测方式 | 自动响应 | 人工介入 |
|------|----------|----------|----------|
| 主服务崩溃 | 心跳超时 | 重启服务 | 如果重启失败 |
| 内存泄漏 | 资源监控 | 通知 + 重启 | 诊断根因 |
| 网络分区 | 连接失败 | 切换到离线模式 | 恢复后同步 |
| 配置错误 | 启动失败 | 回滚到上次配置 | 修复配置 |
| 外部API故障 | 错误率上升 | 降级服务 | 等待API恢复 |

### 9.2 降级服务模式

```yaml
degraded_mode:
  enabled_features:
    - basic_chat
    - status_check
    - emergency_notifications
  
  disabled_features:
    - web_browsing
    - file_operations
    - external_integrations
  
  message_template: |
    ⚠️ 系统正在运行降级模式
    
    部分功能暂时不可用。紧急事务请直接联系管理员。
    
    当前状态: {status}
    预计恢复: {estimated_recovery}
```

---

## 10. 实施清单

### 10.1 部署前检查

- [ ] 配置文件已审核
- [ ] 权限边界已测试
- [ ] 告警通知已配置
- [ ] 熔断机制已启用
- [ ] 回滚方案已准备
- [ ] 团队培训已完成

### 10.2 运维手册位置

```
~/.openclaw/
├── config/
│   └── rescue-robot.json      # 救援机器人配置
├── runbooks/
│   └── rescue-operations.md   # 运维手册
├── logs/
│   └── rescue-events.log      # 救援事件日志
└── state/
    └── rescue-state.json      # 当前状态
```

---

## 11. 附录

### A. 消息模板

**告警消息:**
```
🚨 救援机器人告警

时间: {timestamp}
触发原因: {reason}
主服务状态: {main_status}

诊断信息:
{diagnostic_summary}

正在执行: {current_action}
```

**恢复消息:**
```
✅ 服务已恢复

中断时长: {downtime}
根因: {root_cause}
已执行操作: {actions}

详细报告: {report_url}
```

### B. 相关文档

- OpenClaw Gateway 配置指南
- Cron 任务配置参考
- 健康检查最佳实践
- 事件响应流程 (Incident Response)

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0 | 2026-02-16 | AI Agent | 初始草案 |

---

_此文档是基线版本，应根据实际部署环境进行调整。_
