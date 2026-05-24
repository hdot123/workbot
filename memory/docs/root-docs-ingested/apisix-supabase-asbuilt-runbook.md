# APISIX / 内网 Supabase / MySQL / PostgreSQL 实施说明与运维手册

## 1. 文档目的

本文档记录当前已经落地的 APISIX 统一暴露架构，文档类型为：

- 实施说明（as-built）
- 运维手册（runbook）

本文档不是抽象规范，也不是未来方案设计文档。其目标是：

- 准确描述当前系统已经部署成什么样
- 说明当前链路如何生效
- 提供可执行的排查、验证、回滚方法
- 明确 APISIX、内网 Supabase、内网 MySQL、内网 PostgreSQL 与外网 Supabase 备份链路的职责边界

---

## 2. 架构概览

当前链路如下：

```text
应用 / 客户端
  -> APISIX（内网唯一对应用暴露的入口）
      -> 内网 Supabase gateway（HTTP upstream）
          -> 内网 PostgreSQL
      -> 内网 MySQL（stream upstream）
      -> 内网 PostgreSQL（stream upstream）

外网 Supabase
  -> 备份内网 Supabase
```

### 2.1 统一暴露规则

- 内网环境对应用层只暴露 `APISIX`。
- 内网环境优先于本机环境；本机数据库实例只作为备份/应急使用，不作为默认业务或维护入口。
- `1Password` 中记录的地址、端口、账号、凭据与备注说明视为 `100%` 正确的唯一运维真源；一旦与本地文档、脚本参数或人工记忆冲突，一律以 `1Password` 为准，先纠正文档与脚本，再执行维护动作。
- `APISIX` 当前承载三类正式入口：
  - `Supabase HTTP` 业务链路：`APISIX -> 内网 Supabase gateway -> 内网 PostgreSQL`，承载业务主库、向量数据库，以及从 `MySQL` 汇入后的基础数据
  - `MySQL stream` 业务链路：`APISIX -> 内网 MySQL stream`，承载爬虫采集/落库侧存储
  - `PostgreSQL stream` 业务链路：`APISIX -> 内网 PostgreSQL stream`，承载经 APISIX 暴露的 PostgreSQL 协议流量
- 内网 `Supabase`、`MySQL`、`PostgreSQL` 只作为上游或维护对象，不作为应用直连入口。
- 应用层访问内网 Supabase 走 `http://apisix.tail5e888.ts.net:9080/supabase/...`。
- 应用层访问内网 MySQL 数据走 `apisix.tail5e888.ts.net:3306` 的 APISIX stream 入口。
- 经 APISIX 暴露的 PostgreSQL 协议入口为 `apisix.tail5e888.ts.net:5432`。
- 向量数据库 / embedding / vector index 只允许落在 `PostgreSQL` 业务链路，不允许写入 `MySQL`。
- 外网 `Supabase` 只承担内网 `Supabase` 的备份职责，不作为当前应用主通路。

### 2.2 职责划分

| 组件 | 当前职责 | 不负责的内容 |
|---|---|---|
| APISIX | 统一入口、客户端业务 key 校验、路径改写、向上游注入 Supabase Anon Key、HTTP / stream 转发 | 不管理 MySQL / PostgreSQL schema / table / function；不管理 Supabase 内部对象 |
| 内网 Supabase gateway | 作为内网 Supabase 的 HTTP gateway，承接 `auth`、`rest`、`storage` 等服务请求 | 不负责 APISIX 客户端业务 key 校验；不作为应用默认直连入口 |
| 内网 PostgreSQL | 承载内网 Supabase 的数据库对象、业务主库、向量数据库，以及从 MySQL 汇入后的基础数据 | 不负责 APISIX 路由、Consumer、上游转发策略；不对应用层直接暴露 |
| 内网 MySQL | 承载爬虫采集/落库侧存储，是基础数据的源侧之一 | 不负责 APISIX 鉴权与转发策略；不对应用层直接暴露；不承载向量数据库；不是最终业务真源 |
| 外网 Supabase | 备份内网 Supabase | 不作为当前应用主通路；不替代内网数据库维护链路 |

### 2.3 当前生效链路

当前内网对应用生效的入口有三类，且都统一收敛到 APISIX：

- Supabase HTTP 业务链路（最终落到内网 PostgreSQL）:
  - 客户端访问 `http://apisix.tail5e888.ts.net:9080/supabase/...`
  - 客户端侧唯一需要持有的凭据是 APISIX 业务 key
  - APISIX 校验通过后：
    - 去掉 `/supabase` 前缀
    - 自动向上游注入 `apikey` 和 `Authorization: Bearer`
  - 内网 Supabase gateway 收到的是 APISIX 注入后的合法业务请求
  - 该链路承载业务主库、向量数据库，以及从 MySQL 汇入后的基础数据
- MySQL 业务链路（stream 暴露）:
  - 客户端访问 `apisix.tail5e888.ts.net:3306`
  - APISIX stream proxy 将 TCP 流量转发到 `192.168.88.17:3306`
  - 该链路承载爬虫采集/落库侧存储，不承载向量数据库
  - 应用层不直接暴露 `192.168.88.17:3306`
- PostgreSQL 业务链路（stream 暴露）:
  - 客户端访问 `apisix.tail5e888.ts.net:5432`
  - APISIX stream proxy 将 TCP 流量转发到 `192.168.88.16:5432`
  - 该链路承载 PostgreSQL 协议流量，向量数据库能力仍只允许落在 PostgreSQL
  - 应用层不直接暴露 `192.168.88.16:5432`
- 外网 Supabase:
  - 当前只承担内网 Supabase 的备份职责
  - 不作为应用实时业务流量入口

---

## 3. 当前部署信息

### 3.1 环境信息

| 项 | 当前值 |
|---|---|
| APISIX 运行模式 | `traditional + etcd + Admin API` |
| APISIX 主机 | `192.168.88.11` |
| APISIX Admin API | `http://192.168.88.11:9180` |
| APISIX Supabase HTTP 业务入口 | `http://apisix.tail5e888.ts.net:9080/supabase/...` |
| APISIX MySQL 业务入口 | `apisix.tail5e888.ts.net:3306` |
| APISIX PostgreSQL 业务入口 | `apisix.tail5e888.ts.net:5432` |
| 内网 Supabase gateway | `http://192.168.88.16:8000` |
| 内网 PostgreSQL | `192.168.88.16:5432`（维护侧） |
| 内网 MySQL | `192.168.88.17:3306`（维护侧） |
| 本机 PostgreSQL | 仅备份 / 应急使用，不作为默认入口 |
| 外网 Supabase | 备份内网 Supabase 使用 |
| HTTPS 自动化 | 当前未启用 |
| stream proxy | 已启用（`3306 -> 3306`，`5432 -> 5432`） |

### 3.2 APISIX 已部署对象

| 对象类型 | 名称 | 作用 |
|---|---|---|
| upstream | `supabase-gateway-http-v1` | 指向 `192.168.88.16:8000` 的 HTTP upstream |
| route | `supabase-route-http-v1` | 旧版纯转发路由，作为回滚基础 |
| route | `supabase-route-http-v2` | 当前生效路由，增加 APISIX 业务 key 校验与 Supabase key 注入 |
| consumer | `supabase_client_v1` | 客户端业务 key 所属 Consumer |
| stream_route | `mysql-stream-3306-v1` | 将 `apisix.tail5e888.ts.net:3306` 转发到 `192.168.88.17:3306` |
| stream_route | `postgres-stream-5432-v1` | 将 `apisix.tail5e888.ts.net:5432` 转发到 `192.168.88.16:5432` |

### 3.3 密钥与凭据说明

| 密钥类型 | 用途 | 当前存放方式 |
|---|---|---|
| APISIX Admin Key | 调用 `9180` Admin API 管理 APISIX 对象 | 存于 1Password |
| APISIX 业务 key | 客户端访问 `/supabase/*` 时提交给 APISIX | 存于 1Password |
| Supabase Anon Key | APISIX 在转发到 Supabase gateway 前自动注入的上游业务 key | 来自现有安全存储；当前已写入 APISIX v2 route 配置 |

说明：

- 文档不展示任何明文密钥。
- 当前没有新生成 Supabase key；使用的是既有业务 key。
- v2 通过更高 `priority: 10` 覆盖 `/supabase` 与 `/supabase/*`，v1 保留用于回滚。

---

## 4. 当前请求链路说明

### 4.1 客户端不带 APISIX 业务 key

请求示例：

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health
```

当前行为：

- 请求先进入 APISIX
- 命中 `supabase-route-http-v2`
- `key-auth` 校验失败
- APISIX 直接返回 `401 Unauthorized`

当前语义特征：

- `Server: APISIX/3.9.1`
- 返回的是 APISIX 的 key-auth 拦截语义
- 不是 Supabase 的 “No API key found in request”

这说明：

- 请求未被放行到上游
- `/supabase` 入口已经由 APISIX 接管

### 4.2 客户端带 APISIX 业务 key

请求示例：

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>"
```

当前行为：

1. APISIX 先校验客户端提交的 APISIX 业务 key
2. 校验通过后：
   - 使用 `proxy-rewrite` 去掉 `/supabase` 前缀
   - 将上游请求头改写为：
     - `apikey: <SUPABASE_ANON_KEY>`
     - `Authorization: Bearer <SUPABASE_ANON_KEY>`
3. 请求转发到 `http://192.168.88.16:8000/...`
4. Supabase gateway 正常处理请求

验证结果已经确认：

- `GET /supabase/auth/v1/health` 返回 `200 OK`
- `GET /supabase/rest/v1/` 返回 `200 OK`

### 4.3 客户端自带错误 Authorization 时的行为

请求示例：

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>" \
  -H "Authorization: Bearer totally-wrong-client-token"
```

当前行为：

- 仍然返回 `200 OK`

说明：

- 上游最终收到的不是客户端自带的错误 `Authorization`
- 而是 APISIX `proxy-rewrite.headers.set` 注入的 Supabase Anon Key

### 4.4 为什么客户端不需要直接持有 Supabase Anon Key

原因如下：

- 客户端只需要知道 APISIX 业务 key
- APISIX 在入口层完成客户端鉴权
- 通过后由 APISIX 统一注入上游需要的 Supabase Anon Key
- 客户端无需感知内网 Supabase gateway 的真实业务 key
- 客户端也不应直连内网 MySQL / PostgreSQL
- 这样可以将“客户端入口鉴权”与“上游服务凭据”分离

---

## 5. APISIX 配置对象说明

### 5.1 upstream `supabase-gateway-http-v1`

职责：

- 定义 Supabase gateway 的上游节点
- 作为 v1、v2 route 共用的上游对象
- 当前仅负责 HTTP 转发，不承担鉴权逻辑

脱敏示例：

```json
{
  "id": "supabase-gateway-http-v1",
  "name": "supabase-gateway-http-v1",
  "type": "roundrobin",
  "scheme": "http",
  "pass_host": "node",
  "nodes": {
    "192.168.88.16:8000": 1
  }
}
```

### 5.2 route `supabase-route-http-v1`

职责：

- 旧版纯转发路由
- 仅处理路径改写并转发到 Supabase gateway
- 不做 APISIX 业务 key 校验
- 当前保留，用于回滚

脱敏示例：

```json
{
  "id": "supabase-route-http-v1",
  "name": "supabase-route-http-v1",
  "priority": 0,
  "uris": ["/supabase", "/supabase/*"],
  "upstream_id": "supabase-gateway-http-v1",
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/supabase/?(.*)$", "/$1"]
    }
  }
}
```

### 5.3 route `supabase-route-http-v2`

职责：

- 当前生效路由
- 对 `/supabase` 与 `/supabase/*` 做入口鉴权
- 自动注入 Supabase Anon Key
- 使用更高优先级覆盖 v1

脱敏示例：

```json
{
  "id": "supabase-route-http-v2",
  "name": "supabase-route-http-v2",
  "priority": 10,
  "uris": ["/supabase", "/supabase/*"],
  "upstream_id": "supabase-gateway-http-v1",
  "plugins": {
    "key-auth": {
      "hide_credentials": true
    },
    "proxy-rewrite": {
      "regex_uri": ["^/supabase/?(.*)$", "/$1"],
      "headers": {
        "set": {
          "apikey": "<SUPABASE_ANON_KEY>",
          "Authorization": "Bearer <SUPABASE_ANON_KEY>"
        }
      }
    }
  }
}
```

关键说明：

- `priority: 10` 使 v2 在相同 URI 下优先生效
- `hide_credentials: true` 使客户端 APISIX 业务 key 不再原样向上游透传
- `proxy-rewrite.headers.set` 负责覆盖并注入上游所需凭据

### 5.4 consumer `supabase_client_v1`

职责：

- 表示允许访问 `/supabase/*` 的客户端身份
- 为 `key-auth` 提供 APISIX 业务 key 绑定对象
- 当前名称必须使用下划线形式，因为 APISIX `username` 不接受 `-`

脱敏示例：

```json
{
  "username": "supabase_client_v1",
  "plugins": {
    "key-auth": {
      "key": "<APISIX_CLIENT_KEY>"
    }
  }
}
```

---

## 6. 验证方法

本节用于运维与开发侧日常验证，不依赖仓库外的明文密钥，全部使用占位符表示。

### 6.1 检查 APISIX 对象是否存在

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/upstreams/supabase-gateway-http-v1
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v1
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v2
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/consumers/supabase_client_v1
```

期望结果：

- upstream、v1 route、v2 route、consumer 均可回读
- v2 route 的 `priority` 为 `10`

### 6.2 不带 APISIX 业务 key 的验证

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health
```

期望结果：

- `401 Unauthorized`
- `Server: APISIX/3.9.1`
- 响应语义为 APISIX key-auth 拦截

判定要点：

- 如果返回的是 Supabase “No API key found” 语义，则说明 v2 没有正常接管
- 如果返回的是 APISIX key-auth 语义，则说明入口鉴权生效

### 6.3 带 APISIX 业务 key 的验证

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>"
```

期望结果：

- `200 OK`
- `Server: APISIX/3.9.1`
- 响应体返回 GoTrue 健康信息

### 6.4 REST 接口验证

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/rest/v1/ \
  -H "apikey: <APISIX_CLIENT_KEY>" \
  -H "Accept: application/openapi+json"
```

期望结果：

- `200 OK`
- `Content-Type: application/openapi+json`
- `Content-Profile: public`

### 6.5 本机回环验证

在 APISIX 主机上执行：

```bash
curl -i http://127.0.0.1:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>"
```

期望结果：

- `200 OK`

### 6.6 如何判断请求确实经过 APISIX

关键证据：

- 响应头包含 `Server: APISIX/3.9.1`
- 同时可看到 `Via: 1.1 kong/3.9.1`
- 同时可看到 `X-Kong-Request-Id`

解释：

- `Server: APISIX/3.9.1` 说明入口响应来自 APISIX
- `Via: 1.1 kong/3.9.1`、`X-Kong-Request-Id` 说明请求进一步到达了 Supabase gateway

### 6.7 如何判断注入的 Supabase key 已生效

方法一：客户端伪造错误 Authorization

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>" \
  -H "Authorization: Bearer totally-wrong-client-token"
```

期望结果：

- 仍然 `200 OK`

说明：

- 上游收到的不是客户端伪造值
- 而是 APISIX 注入值

方法二：用 APISIX 业务 key 直接打上游

```bash
curl -i http://192.168.88.16:8000/rest/v1/ \
  -H "apikey: <APISIX_CLIENT_KEY>" \
  -H "Authorization: Bearer <APISIX_CLIENT_KEY>" \
  -H "Accept: application/openapi+json"
```

期望结果：

- `401 Unauthorized`

说明：

- APISIX 业务 key 本身不是上游可接受的 Supabase 业务 key
- 如果同样的客户端请求通过 APISIX 却能返回 `200 OK`，则证明 APISIX 注入的 Supabase key 已生效

---

## 7. 回滚方法

当前回滚目标是：从 v2 恢复到 v1 的纯转发状态。

### 7.1 删除 v2 route

```bash
curl -sS -X DELETE \
  "http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v2" \
  -H "X-API-KEY: <APISIX_ADMIN_KEY>"
```

### 7.2 删除 v2 Consumer

```bash
curl -sS -X DELETE \
  "http://192.168.88.11:9180/apisix/admin/consumers/supabase_client_v1" \
  -H "X-API-KEY: <APISIX_ADMIN_KEY>"
```

### 7.3 检查对象已不存在

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v2
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/consumers/supabase_client_v1
```

期望结果：

- 返回对象不存在或 key not found

### 7.4 验证已恢复为 v1 纯转发

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health
```

回滚后的期望结果：

- 请求不再被 APISIX key-auth 拦截
- 请求会被纯转发到 Supabase gateway
- 响应语义回到 Supabase 上游侧的鉴权结果

说明：

- v1 route 与 upstream 保持原样，因此删除 v2 对象即可恢复

---

## 8. 风险与边界

### 8.1 APISIX 当前管理边界

APISIX 当前管理的是：

- Supabase 的访问入口
- 客户端业务 key 校验
- 请求路径改写
- 上游请求头注入
- HTTP 转发链路

APISIX 当前**不管理**：

- PostgreSQL database / schema / table / function
- Supabase 内部数据库对象
- Supabase 数据迁移
- PostgreSQL 用户、角色、权限对象

### 8.2 数据库对象管理边界

数据库结构变更应通过数据库侧受控方式完成，例如：

- SQL Editor
- migration
- `psql`
- 受控管理服务

APISIX 不能直接创建 PostgreSQL schema，也不是数据库对象管理器。

### 8.3 当前使用的是 Anon Key，不是 Service Role Key

当前注入到上游的是 **Supabase Anon Key**，不是 Service Role Key。其意义是：

- APISIX 代表客户端进入 Supabase 的是“匿名业务访问”边界
- 不应具备 Service Role 级别的高权限
- 可以减少误用高权限 key 的风险

权限边界说明：

- Anon Key 适用于面向业务 API 的受控访问入口
- Service Role Key 通常具有更高权限，不适合作为公开入口代理默认注入值
- 因此当前设计刻意使用 Anon Key 作为上游注入凭据

### 8.4 当前已知风险

1. Supabase Anon Key 当前存在于 APISIX route 配置中，能够读取 APISIX Admin API 的管理员可以看到该值。  
2. v1 与 v2 共用相同 URI，当前依赖 `priority: 10` 让 v2 覆盖生效；未来若新增更高优先级同路径 route，可能绕开当前入口控制链路。

---

## 9. 后续建议

1. 后续如继续接入其他后端服务，继续沿用统一入口模式：应用层只暴露 APISIX，上游服务凭据由 APISIX 注入或转发。  
2. 内网 MySQL / PostgreSQL 继续只作为维护对象；数据库结构变更应独立走数据库迁移流程，不应把直连维护口径写成应用默认入口。  
3. 外网 Supabase 继续只承担内网 Supabase 备份职责；如未来要承担其他职责，必须单独立项并改写 runbook。  
4. 后续若启用 HTTPS，应单独规划域名、证书、TLS 终止位置与证书更新流程，不与当前 HTTP 接入变更混做。

---

## 10. 术语说明

| 术语 | 说明 |
|---|---|
| APISIX Admin Key | 用于调用 APISIX `9180` Admin API 的管理密钥 |
| APISIX 业务 key | 客户端访问 `/supabase/*` 时提交给 APISIX 的入口业务凭据 |
| Supabase Anon Key | APISIX 在转发到 Supabase gateway 前自动注入的上游业务 key |
| Supabase gateway | 内网 Supabase 的 API gateway，当前地址为 `http://192.168.88.16:8000` |
