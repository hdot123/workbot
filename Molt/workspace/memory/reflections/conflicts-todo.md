
# 待裁决清单 (Conflicts Todo)

> 用途：记录发现的"同一字段多版本"冲突项，等待人类裁决
> 创建日期：2026-03-02
> 维护者：Molt King
> 状态：初始化

---

## 冲突项列表

### 1. node-11 的角色定义

**字段名**：node-11 角色定义

**版本A**：
- 描述：node-11 是多租客环境部署节点
- 来源文件：`kb/decisions/2026-02-28-node-11-multi-tenant.md`
- 详细信息：
  - 部署模式: Mise + PM2 + 多账户共享
  - 业务账户: user1, user2, user3
  - 端口分配: 18810, 18820, 18830
  - 反向代理: Caddy

**版本B**：
- 描述：node-11 没有出现在节点角色定义表中
- 来源文件：`kb/projects/main.md`
- 详细信息：
  - 节点角色定义表只包含：node-01, node-00, node-12, node-13
  - 缺少 node-11 的定义

**裁决建议**：
- 选项1：将 node-11 添加到 `projects/main.md` 的节点角色定义表中
- 选项2：废弃 node-11，将其从决策中移除
- 选项3：保留 node-11，但标记为"临时节点"或"特殊用途节点"

**状态**：⏳ 待裁决

---

### 2. node-11 的 Tailscale IP 地址

**字段名**：node-11 Tailscale IP

**版本A**：
- 描述：100.100.1.11
- 来源文件：`2026-02-28.md`
- 详细信息：
  - 节点: node-11 (100.100.1.11)
  - 系统: Debian 13 (trixie)
  - CPU: Common KVM processor, Family 15
  - 内存: 11GB RAM

**版本B**：
- 描述：未定义
- 来源文件：`kb/projects/main.md`
- 详细信息：
  - 节点角色定义表中没有 node-11
  - 没有 Tailscale IP 信息

**裁决建议**：
- 如果保留 node-11，需要在 `projects/main.md` 中添加其 Tailscale IP (100.100.1.11)
- 如果废弃 node-11，需要在 `2026-02-28.md` 中标记为已废弃

**状态**：⏳ 待裁决

---

## 裁决流程

1. **阅读冲突项**：仔细阅读每个冲突项的版本A和版本B
2. **选择裁决**：
   - 选择A：采用版本A
   - 选择B：采用版本B
   - 合并：合并两个版本
   - 废弃：标记为已废弃
3. **更新文件**：根据裁决结果更新相关文件
4. **标记状态**：将冲突项状态从"待裁决"改为"已裁决"

---

## 统计

- 总冲突项：2
- 待裁决：2
- 已裁决：0
- 已废弃：0

---

*最后更新：2026-03-02 03:17 (Asia/Shanghai)*

---

## 【V2】严格冲突清单（2026-03-02 03:26）

> 扫描规则：同一字段在不同文件中出现"两个不同的具体值"才算冲突
> 扫描范围：workspace/memory/ 下所有 .md 文件
> 扫描优先字段：node-00/public_ip, node-01/public_ip, node-01/tailscale_ip, node-11/ports, node-11/tailscale_ip, supabase project_ref(s)

---

### 真正的冲突（同一字段有两个不同的具体值）

#### 1. 主模型配置 (primary_model)

**field**: primary_model

**value_A**: anthropic/glm-4.7
- source_path: `2026-02-26.md:122`
- evidence: "**主模型**：anthropic/glm-4.7 (智谱 GLM-4.7)"

**value_B**: zai/glm-5
- source_path: `2026-02-16.md:40`
- evidence: "- 主模型: zai/glm-5"
- source_path: `2026-02-26-request-timed-out-before-a-res.md:41`
- evidence: "| 模型配置 | ✅ zai/glm-5 | 主力模型正常 |"

**状态**: ⏳ 待裁决

---

### GAP 列表（信息缺口）

> "缺失/未定义/未出现"只记为 GAP（信息缺口），不是冲突

#### 1. node-11 在节点角色定义表中缺失

**field**: node-11 角色定义

**GAP 描述**:
- 在 `kb/decisions/2026-02-28-node-11-multi-tenant.md` 中，node-11 是多租客环境部署节点
- 在 `2026-02-28.md` 中，node-11 有 Tailscale IP (100.100.1.11) 和端口分配 (18810, 18820, 18830)
- 但在 `kb/projects/main.md` 的节点角色定义表中，没有 node-11 的记录

**影响**: 节点信息不完整，可能导致运维混乱

**建议**: 将 node-11 添加到 `projects/main.md` 的节点角色定义表中

---

#### 2. node-11/public_ip 缺失

**field**: node-11/public_ip

**GAP 描述**:
- node-11 有 Tailscale IP (100.100.1.11)
- 但没有公网 IP 的记录

**影响**: 无法从外网访问 node-11

**建议**: 确认 node-11 是否有公网 IP，如果有则记录

---

#### 3. node-11/角色描述缺失

**field**: node-11/角色描述

**GAP 描述**:
- node-11 在决策文件中被描述为"多租客环境部署节点"
- 但在节点角色定义表中没有统一的描述

**影响**: 节点角色不清晰

**建议**: 统一 node-11 的角色描述

---

### 扫描统计

- **真正的冲突**: 1 条
- **GAP（信息缺口）**: 3 条
- **扫描字段**: node-00/public_ip, node-01/public_ip, node-01/tailscale_ip, node-11/ports, node-11/tailscale_ip, supabase project_ref(s), primary_model

---

*V2 更新：2026-03-02 03:26 (Asia/Shanghai)*
