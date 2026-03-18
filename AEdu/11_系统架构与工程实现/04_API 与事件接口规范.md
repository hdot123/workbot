# API 与事件接口规范

> 文档编号：ARCH-004  
> 版本：V1.0  
> 创建日期：2024  
> 最后更新：待定  
> 维护人：系统架构与工程实现负责人

---

## 1. 文档目的

本文档用于定义教育孪生项目中的 API 与事件接口规范，包括接口设计原则、请求响应结构、同步 API、异步事件、错误码、版本控制与接口边界。

本文档重点回答以下问题：

1. 系统对外和对内的接口如何统一设计
2. 哪些能力适合 API，哪些适合事件
3. 不同模块之间如何通过接口协同
4. 如何保证接口可扩展、可追踪、可审计
5. 如何避免接口风格混乱和事件语义漂移

---

## 2. 接口体系定义

教育孪生项目的接口体系分为两类：

1. 同步 API 接口
2. 异步事件接口

### 2.1 同步 API 接口
适用于：
- 页面查询
- 配置管理
- 手工录入
- 立即返回结果的操作
- 后台管理动作

### 2.2 异步事件接口
适用于：
- OCR 解析
- 学习事件生成
- StudentTwinAgent 状态更新
- 图谱写入
- 报告生成
- 推演任务处理

---

## 3. 设计原则

### 3.1 资源与动作分离
查询和管理类操作优先用资源型 API；长耗时、链式处理优先用事件驱动。

### 3.2 接口语义清晰
接口名必须表达业务含义，不允许"doTask""handleData"这种烟雾弹命名。

### 3.3 幂等优先
关键写接口和关键消费事件必须支持幂等。

### 3.4 版本可控
API 和事件都应具备版本策略。

### 3.5 可追踪
接口请求和事件流转必须能关联 request_id / event_id / trace_id。

### 3.6 错误可解释
错误码和错误信息必须能帮助定位问题，不要只会吐 500 和一脸茫然。

---

## 4. 基础接口规范

### 4.1 请求头建议

| Header | 说明 |
|--------|------|
| Authorization | 身份认证 |
| X-Tenant-Id | 租户标识 |
| X-Request-Id | 请求唯一标识 |
| X-Trace-Id | 链路追踪标识 |
| X-Client-Version | 客户端版本 |
| Content-Type | 内容类型 |

### 4.2 通用响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "REQ_20240420_001",
  "trace_id": "TRACE_20240420_001"
}
```

### 4.3 通用分页结构

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

---

## 5. API 分类

建议 API 按模块划分为以下几类：

1. 接入类 API
2. 学生孪生类 API
3. 知识底座类 API
4. 观察层类 API
5. 报告类 API
6. 推演类 API
7. 管理与配置类 API

---

## 6. 接入类 API

### 6.1 原始输入上传接口

**POST** `/api/v1/ingest/raw-inputs`

用途：

- 上传文本
- 上传图片/扫描件
- 上传 PDF
- 上传批量文件

请求示例：

```json
{
  "student_id": "STU_000123",
  "source_role": "parent",
  "source_channel": "wechat",
  "input_type": "text",
  "payload": {
    "text": "今天物理作业做完了，错了两题"
  },
  "event_time": "2024-04-20T19:30:00+08:00"
}
```

返回：

- raw_input_id
- 接收状态
- 后续处理任务号（如异步）

---

### 6.2 手工事件录入接口

**POST** `/api/v1/ingest/manual-events`

用途：

- 老师或运营后台手工录入结构化事件

---

## 7. 学生孪生类 API

### 7.1 获取学生当前态

**GET** `/api/v1/students/{student_id}/twin`

用途：

- 查询 StudentTwinAgent 当前摘要状态

返回建议包含：

- 基础绑定信息
- 当前状态摘要
- 当前风险等级
- 当前关注点
- 最新更新时间

### 7.2 获取学生知识点状态

**GET** `/api/v1/students/{student_id}/knowledge-states`

用途：

- 查询知识点掌握快照

### 7.3 获取学生状态变更记录

**GET** `/api/v1/students/{student_id}/state-history`

用途：

- 查询状态变化轨迹摘要

---

## 8. 知识底座类 API

### 8.1 获取章节树

**GET** `/api/v1/knowledge/chapters`

支持条件：

- curriculum_version_id
- subject
- grade_level

### 8.2 获取知识点列表

**GET** `/api/v1/knowledge/knowledge-points`

支持条件：

- chapter_node_id
- curriculum_version_id
- subject

### 8.3 获取知识点详情

**GET** `/api/v1/knowledge/knowledge-points/{knowledge_id}`

返回：

- 定义
- 挂载章节
- 关联能力点
- 关联误区
- 关联题型

---

## 9. 观察层类 API

### 9.1 获取家长端观察首页

**GET** `/api/v1/observation/parent/students/{student_id}/overview`

### 9.2 获取老师端学生观察页

**GET** `/api/v1/observation/teacher/students/{student_id}/overview`

### 9.3 获取学校端看板摘要

**GET** `/api/v1/observation/school/dashboard`

支持条件：

- school_id
- class_id
- grade_level
- subject

---

## 10. 报告类 API

### 10.1 创建报告任务

**POST** `/api/v1/reports/tasks`

请求示例：

```json
{
  "report_type": "weekly",
  "target_role": "parent",
  "student_id": "STU_000123",
  "report_period": {
    "start_date": "2024-04-15",
    "end_date": "2024-04-21"
  }
}
```

### 10.2 查询报告任务状态

**GET** `/api/v1/reports/tasks/{task_id}`

### 10.3 获取报告详情

**GET** `/api/v1/reports/{report_id}`

---

## 11. 推演类 API

### 11.1 创建推演任务

**POST** `/api/v1/simulations/tasks`

用途：

- 发起后台推演任务

请求示例：

```json
{
  "student_id": "STU_000123",
  "scenario_type": "intervention_effect",
  "action_set": ["ACT_PHY_PRACTICE_001"],
  "time_window": "2_weeks"
}
```

### 11.2 查询推演任务状态

**GET** `/api/v1/simulations/tasks/{simulation_id}`

### 11.3 获取推演结果

**GET** `/api/v1/simulations/{simulation_id}`

注意：

- 高风险推演结果必须受权限控制
- 不同角色返回不同字段集合

---

## 12. 反馈类 API

### 12.1 提交观察反馈

**POST** `/api/v1/feedbacks/observation`

### 12.2 提交报告反馈

**POST** `/api/v1/feedbacks/reports`

### 12.3 提交状态校正反馈

**POST** `/api/v1/feedbacks/state-corrections`

作用：

- 将家长/老师反馈回流到事件系统和人工校准通道

---

## 13. 事件接口分类

建议内部事件至少分为以下几类：

1. 原始输入事件
2. 学习事件
3. 状态更新事件
4. 图谱写入事件
5. 报告任务事件
6. 推演任务事件
7. 反馈事件

---

## 14. 事件基础结构

所有事件建议至少包含以下字段：

| 字段 | 说明 |
|------|------|
| event_id | 事件唯一标识 |
| event_name | 事件名称 |
| event_version | 事件版本 |
| event_time | 事件发生时间 |
| producer | 事件生产方 |
| tenant_id | 租户标识 |
| trace_id | 链路追踪标识 |
| payload | 事件内容 |
| metadata | 元数据 |

### 14.1 基础事件样例

```json
{
  "event_id": "EVT_20240420_001",
  "event_name": "learning.event.created",
  "event_version": "1.0",
  "event_time": "2024-04-20T19:31:08Z",
  "producer": "event-engine",
  "tenant_id": "SCH_SZ_001",
  "trace_id": "TRACE_20240420_001",
  "payload": {},
  "metadata": {
    "request_id": "REQ_20240420_001"
  }
}
```

---

## 15. 关键事件定义

### 15.1 原始输入接收事件

`ingest.raw_input.received`

用途：

- 原始输入入库后广播

### 15.2 学习事件生成事件

`learning.event.created`

用途：

- 标准学习事件生成后广播

### 15.3 StudentTwinAgent 更新事件

`twin.state.updated`

用途：

- 学生状态更新完成后广播

### 15.4 图谱写入事件

`graph.memory.written`

用途：

- 图谱记忆写入完成后广播

### 15.5 报告任务创建事件

`report.task.created`

### 15.6 报告生成完成事件

`report.generated`

### 15.7 推演任务创建事件

`simulation.task.created`

### 15.8 推演完成事件

`simulation.completed`

### 15.9 反馈提交事件

`feedback.submitted`

---

## 16. 事件语义规范

### 16.1 命名规范

建议使用：`领域。对象。动作`

示例：

- `learning.event.created`
- `twin.state.updated`
- `report.generated`

### 16.2 语义原则

- 名称表达清晰
- 动作使用统一时态
- 同一类事件不要多套命名风格混用

---

## 17. 幂等与去重规范

### 17.1 API 幂等

以下接口建议支持幂等键：

- 原始输入上传
- 手工事件录入
- 推演任务创建
- 报告任务创建

### 17.2 事件去重

事件消费端应至少使用以下方式之一：

- event_id 去重
- 幂等表
- 业务主键去重

说明：
学习事件和状态更新如果不做幂等，很快就能把一个学生写成平行宇宙版本。

---

## 18. 错误码规范

建议错误码至少分层：

| 范围 | 含义 |
|------|------|
| 0 | 成功 |
| 1000-1999 | 参数与请求错误 |
| 2000-2999 | 鉴权与权限错误 |
| 3000-3999 | 业务状态错误 |
| 4000-4999 | 事件处理错误 |
| 5000-5999 | 系统内部错误 |

### 18.1 示例

- `1001` 参数缺失
- `2001` 未授权
- `2003` 无权限访问该学生
- `3002` 学生不存在
- `4004` 学习事件生成失败
- `5001` 系统异常

---

## 19. 版本控制规范

### 19.1 API 版本

建议路径中显式带版本：`/api/v1/...`

### 19.2 事件版本

事件体中显式带：`event_version`

### 19.3 演进原则

- 优先向后兼容
- 重大变更升级版本
- 废弃接口保留迁移窗口

---

## 20. 安全与权限规范

### 20.1 权限控制

不同角色可访问的接口范围必须不同。

### 20.2 敏感字段过滤

- 家长不能直接查看后台推演高风险字段
- 学校端默认不暴露过多个体敏感细节
- 内部审计字段不对前台开放

### 20.3 审计要求

以下操作必须审计：

- 状态手工修改
- 高风险推演查看
- 报告导出
- 规则更新
- 权限变更

---

## 21. 模块边界规则

### 21.1 API 边界

- 观察层 API 不直接修改 StudentTwinAgent 核心状态
- 知识底座 API 不直接暴露底层表结构细节给前台
- 推演 API 不应绕过状态层自行构造学生态

### 21.2 事件边界

- 事件层只广播语义明确的业务事件
- 不广播难以复用的临时实现事件
- 图谱写入事件与状态更新事件应区分开

---

## 22. MVP 建议范围

MVP 阶段建议优先实现以下 API / 事件：

### 22.1 API

- 原始输入上传
- 查询学生当前态
- 查询章节树
- 查询知识点列表
- 获取家长端观察页
- 创建周报任务
- 查询报告结果
- 创建推演任务（后台）

### 22.2 事件

- `ingest.raw_input.received`
- `learning.event.created`
- `twin.state.updated`
- `report.task.created`
- `report.generated`
- `simulation.task.created`
- `simulation.completed`

---

## 23. 与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| ARCH-004 API 与事件接口规范 | ARCH-002 系统分层与模块边界 | 接口边界需与模块边界一致 |
| ARCH-004 API 与事件接口规范 | INGEST-007 学习事件生成标准 | 事件接口需承接学习事件标准 |
| ARCH-004 API 与事件接口规范 | TWIN-002 学生 Agent 字段设计 | 学生态查询接口依赖字段设计 |
| ARCH-004 API 与事件接口规范 | OBS-006 报告与解释层设计 | 报告 API 承接报告输出 |
| ARCH-004 API 与事件接口规范 | SIM-003 干预动作库设计 | 推演接口与动作库关联 |

---

## 24. 结论

API 与事件接口规范，是把教育孪生项目从"文档系统"推进到"可协同运行系统"的关键约束层。

如果没有统一接口规范：

- 模块边界会漂
- 事件语义会乱
- 前后台会各说各话
- 审计和追踪会非常痛苦

因此接口体系必须坚持：

- API 负责同步访问
- 事件负责异步驱动
- 语义统一
- 幂等优先
- 版本明确
- 权限可控

---

**文档状态**：已有初稿  
**审批人**：待定  
**下次评审日期**：待定

## 与其他文档的关系

| 文档 | 关联文档 | 关系说明 |
|------|----------|----------|
| ARCH-004 API 与事件接口规范 | ARCH-001 总体技术架构 | 接口规范遵循总体技术架构 |
| ARCH-004 API 与事件接口规范 | ARCH-002 系统分层与模块边界 | 接口规范定义层间交互边界 |
| ARCH-004 API 与事件接口规范 | ARCH-003 核心服务拆分方案 | 接口规范定义服务间通信协议 |
| ARCH-004 API 与事件接口规范 | INGEST-001 微信钉钉接入标准 | 平台接入遵循统一接口规范 |
| ARCH-004 API 与事件接口规范 | INGEST-003 私立学校批量录入端设计 | 批量录入端遵循统一接口规范 |
