# APISIX / 内网 Supabase / MySQL / PostgreSQL 维护与故障定位手册

## 1. 文档目的

本文档用于当前已落地的 APISIX 网关环境的日常维护、故障定位与应急排查。

本文档不是抽象设计规范，也不是实施记录复述。它的目标是：

- 出现故障时，帮助值班人员快速判断问题位于哪一层
- 提供统一、可执行的检查顺序
- 让运维或开发在不依赖记忆的情况下完成快速定位
- 明确哪些对象由 APISIX 管，哪些对象由内网 Supabase / MySQL / PostgreSQL 管

配套文档：

- [APISIX / 内网 Supabase / MySQL / PostgreSQL 实施说明与运维手册](/Users/busiji/workbot/docs/apisix-supabase-asbuilt-runbook.md)

---

## 2. 适用范围

### 2.1 统一暴露口径

- 内网环境对应用层只暴露 `APISIX`。
- 内网环境优先于本机环境；本机数据库实例只作为备份/应急使用，不作为默认业务或维护入口。
- `1Password` 中记录的地址、端口、账号、凭据与备注说明视为 `100%` 正确的唯一运维真源；一旦与本地文档、脚本参数或人工记忆冲突，一律以 `1Password` 为准，先纠正文档与脚本，再执行维护动作。
- `APISIX` 当前承载三类正式入口：
  - `Supabase HTTP` 业务链路：`APISIX -> 内网 Supabase gateway -> 内网 PostgreSQL`，承载业务主库、向量数据库，以及从 `MySQL` 汇入后的基础数据
  - `MySQL stream` 业务链路：`APISIX -> 内网 MySQL stream`，承载爬虫采集/落库侧存储
  - `PostgreSQL stream` 业务链路：`APISIX -> 内网 PostgreSQL stream`，承载经 APISIX 暴露的 PostgreSQL 协议流量
- 内网 `MySQL` 与内网 `PostgreSQL` 只作为维护对象，不作为应用直连入口。
- 内网 `Supabase` 作为 APISIX 的上游 HTTP 服务存在，不作为应用默认直连入口。
- 向量数据库 / embedding / vector index 只允许落在 `PostgreSQL` 业务链路，不允许写入 `MySQL`。
- 外网 `Supabase` 只承担内网 `Supabase` 的备份职责，不承担当前应用主流量。

### 2.2 当前手册覆盖的链路

当前手册覆盖 APISIX 当前对应用暴露的三类已上线入口：

1. **Supabase HTTP 业务链路（最终落到内网 PostgreSQL，承载向量数据库与汇入后的基础数据）**
   - 客户端访问：`http://apisix.tail5e888.ts.net:9080/supabase/...`
   - APISIX 鉴权并注入 Supabase Anon Key
   - 转发到：`http://192.168.88.16:8000/...`
   - 最终落到：内网 PostgreSQL

2. **MySQL 业务链路（stream 暴露，承载爬虫采集/落库侧存储）**
   - 客户端访问：`apisix.tail5e888.ts.net:3306`
   - APISIX stream proxy 转发
   - 转发到：`192.168.88.17:3306`

3. **PostgreSQL 业务链路（stream 暴露，承载 PostgreSQL 协议流量）**
   - 客户端访问：`apisix.tail5e888.ts.net:5432`
   - APISIX stream proxy 转发
   - 转发到：`192.168.88.16:5432`

不覆盖：

- HTTPS 证书自动化
- PostgreSQL schema / table / function 变更
- MySQL 库表结构调整
- Supabase 内部数据库对象变更

---

## 3. 当前已部署拓扑

### 3.1 主机与入口

| 组件 | 地址 | 作用 |
|---|---|---|
| APISIX 主机 | `192.168.88.11` | 网关入口 |
| APISIX Admin API | `http://192.168.88.11:9180` | 配置管理 |
| APISIX Supabase HTTP 业务入口 | `http://apisix.tail5e888.ts.net:9080/supabase/...` | 内网 Supabase HTTP 代理入口，最终落到 PostgreSQL |
| APISIX MySQL 业务入口 | `apisix.tail5e888.ts.net:3306` | 内网 MySQL TCP 代理入口 |
| APISIX PostgreSQL 业务入口 | `apisix.tail5e888.ts.net:5432` | 内网 PostgreSQL TCP 代理入口 |
| 内网 Supabase gateway | `http://192.168.88.16:8000` | 上游 HTTP gateway |
| 内网 PostgreSQL | `192.168.88.16:5432` | PostgreSQL 业务面底层数据库、向量数据库载体，以及汇入后的基础数据承载面 |
| 内网 MySQL 宿主机 | `192.168.88.17` | 上游 MySQL 爬虫采集/落库侧服务 |
| 本机 PostgreSQL | 本机安装但非默认服务面 | 仅备份 / 应急使用 |

### 3.2 当前 APISIX 对象

| 类型 | 名称 | 用途 |
|---|---|---|
| upstream | `supabase-gateway-http-v1` | Supabase HTTP 上游 |
| route | `supabase-route-http-v1` | Supabase 旧版纯转发 |
| route | `supabase-route-http-v2` | 当前生效的 Supabase 鉴权 + 注入路由 |
| consumer | `supabase_client_v1` | APISIX 客户端业务 key 归属 Consumer |
| stream_route | `mysql-stream-3306-v1` | MySQL TCP 转发规则 |
| stream_route | `postgres-stream-5432-v1` | PostgreSQL TCP 转发规则 |

### 3.3 当前 APISIX 模式

当前 APISIX 使用：

- `traditional + etcd + Admin API`
- `http&stream`

这意味着：

- HTTP 路由与 stream 路由同时生效
- 修改 APISIX 配置时，必须同时考虑 HTTP 与 stream 两条链路

---

## 4. 快速定位总表

### 4.1 30 秒定位矩阵

| 现象 | 优先怀疑层 | 第一条检查命令 | 正常结果 |
|---|---|---|---|
| `/supabase/*` 全部超时 | APISIX 容器 / 端口监听 | `ssh ubuntu@192.168.88.11 'ss -lntp | egrep "9080|9180|9443|3306|5432"'` | `9080/9180/9443/3306/5432` 正常监听 |
| `/supabase/*` 返回 401，且语义是 `Missing API key found in request` | APISIX `key-auth` 生效，客户端没带 APISIX key | `curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health` | 返回 APISIX 401 |
| `/supabase/*` 带 APISIX key 仍 401 | v2 route、Consumer、注入头、上游可达性 | 见 6.3 章节 | `200 OK` |
| `/supabase/*` 不通，但 `:9180` 正常 | HTTP route 或上游问题 | 见 6.3.2 与 6.3.3 | route/upstream 均可回读 |
| `3306` 不通，但 `/supabase/*` 正常 | stream 端口或 stream_route 问题 | 见 7.2 ~ 7.4 章节 | `3306` 监听且 stream_route 可回读 |
| `3306` 可连通，但数据库客户端登录失败 | MySQL 账号权限或 MySQL 侧问题 | 仅在维护排障时直连 `192.168.88.17:3306` 对照 | APISIX 与维护直连表现应一致 |
| `5432` 不通，但 `/supabase/*` 正常 | PostgreSQL stream 端口或 stream_route 问题 | 见 7.2 ~ 7.5 章节 | `5432` 监听且 stream_route 可回读 |
| `5432` 可连通，但数据库客户端登录失败 | PostgreSQL 账号权限或 PostgreSQL 侧问题 | 仅在维护排障时直连 `192.168.88.16:5432` 对照 | APISIX 与维护直连表现应一致 |
| `9180` 不可用 | APISIX 容器异常或来源限制 | 见 6.2 章节 | Admin API 200 |

### 4.2 分层判断原则

故障定位时按下面顺序判断，不要跳步：

1. **宿主机 / 容器是否存活**
2. **端口是否监听**
3. **Admin API 是否可读配置对象**
4. **APISIX 是否命中正确对象**
5. **上游是否可达**
6. **协议级行为是否正确**

---

## 5. 标准排障流程

### 5.1 第一步：确认 APISIX 容器与端口

```bash
ssh ubuntu@192.168.88.11 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

```bash
ssh ubuntu@192.168.88.11 'ss -lntp | egrep "9080|9180|9443|3306|5432" || true'
```

正常预期：

- `apisix-gw-test-01` 容器处于 `Up`
- `9080`、`9180`、`9443`、`3306`、`5432` 均在监听

若异常：

- 如果容器不在：先查 `docker compose ps`
- 如果端口不在：优先检查 `config.yaml` 与 `docker-compose.yml` 是否被改坏

### 5.2 第二步：确认 Admin API 正常

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v2
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/stream_routes/mysql-stream-3306-v1
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/stream_routes/postgres-stream-5432-v1
```

正常预期：

- `supabase-route-http-v2` 能回读
- `mysql-stream-3306-v1` 能回读
- `postgres-stream-5432-v1` 能回读

若异常：

- 先确认调用方 IP 是否在 `allow_admin` 范围内
- 再检查 APISIX 容器日志

### 5.3 第三步：按 HTTP 或 stream 分支检查

- Supabase HTTP 问题：走第 6 章
- MySQL stream 问题：走第 7 章
- PostgreSQL stream 问题：走第 7 章

---

## 6. Supabase HTTP 链路定位

### 6.1 先区分“没带 APISIX key”还是“带了也失败”

#### 不带 APISIX 业务 key

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health
```

正常预期：

- `401 Unauthorized`
- `Server: APISIX/3.9.1`
- 语义为 APISIX 的 key-auth 拦截

这表示：

- APISIX v2 路由仍在工作
- 没有直接绕到 Supabase 上游

#### 带 APISIX 业务 key

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>"
```

正常预期：

- `200 OK`
- `Server: APISIX/3.9.1`
- 可见 `Via: 1.1 kong/3.9.1`

如果这里失败，再继续看 6.2 ~ 6.5。

### 6.2 检查 Supabase route 与 Consumer

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/routes/supabase-route-http-v2
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/consumers/supabase_client_v1
```

重点确认：

- `priority = 10`
- `uris = ["/supabase", "/supabase/*"]`
- `key-auth.hide_credentials = true`
- `regex_uri = ["^/supabase/?(.*)$", "/$1"]`
- `headers.set.apikey` 已配置
- `headers.set.Authorization` 已配置

如果这里缺项：

- 说明 route 被覆盖、被误删或被改坏

### 6.3 检查 Supabase upstream

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/upstreams/supabase-gateway-http-v1
```

重点确认：

- 上游节点仍是 `192.168.88.16:8000`
- `scheme = http`
- `pass_host = node`

### 6.4 检查 APISIX 到 Supabase gateway 的可达性

在 APISIX 主机执行：

```bash
ssh ubuntu@192.168.88.11 'curl -i -s http://192.168.88.16:8000/ | sed -n "1,20p"'
```

```bash
ssh ubuntu@192.168.88.11 'curl -i -s http://192.168.88.16:8000/auth/v1/health | sed -n "1,20p"'
```

正常预期：

- 至少 TCP 可达
- HTTP 有响应

### 6.5 如何判断“注入头失效”

使用错误 Authorization 进行对照：

```bash
curl -i http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: <APISIX_CLIENT_KEY>" \
  -H "Authorization: Bearer totally-wrong-client-token"
```

正常预期：

- 仍然返回 `200 OK`

若这里失败：

- 优先怀疑 `proxy-rewrite.headers.set` 丢失
- 或 route 被旧版/其他高优先级 route 覆盖

---

## 7. Stream 链路定位

### 7.1 先看 APISIX stream 端口是否还在监听

```bash
ssh ubuntu@192.168.88.11 'ss -lntp | egrep "3306|5432" || true'
```

正常预期：

- `0.0.0.0:3306`
- `[::]:3306`
- `0.0.0.0:5432`
- `[::]:5432`

若不监听：

- 检查 `config.yaml` 中是否仍有：
  - `proxy_mode: http&stream`
  - `stream_proxy.tcp: [3306, 5432]`
- 检查 `docker-compose.yml` 中是否仍有：
  - `3306:3306`
  - `5432:5432`

### 7.2 回读 stream_route

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/stream_routes/mysql-stream-3306-v1
```

```bash
curl -sS -H "X-API-KEY: <APISIX_ADMIN_KEY>" \
  http://192.168.88.11:9180/apisix/admin/stream_routes/postgres-stream-5432-v1
```

正常预期：

- `mysql-stream-3306-v1.server_port = 3306`
- `mysql-stream-3306-v1.upstream.nodes = 192.168.88.17:3306`
- `postgres-stream-5432-v1.server_port = 5432`
- `postgres-stream-5432-v1.upstream.nodes = 192.168.88.16:5432`
- 两条 `scheme` 都是 `tcp`

若不存在：

- 说明对应 stream_route 被删除或未成功写入

### 7.3 验证 APISIX 本机 TCP 可达性

在 APISIX 主机执行：

```bash
ssh ubuntu@192.168.88.11 'nc -vz -w 3 127.0.0.1 3306 && nc -vz -w 3 192.168.88.11 3306 && nc -vz -w 3 127.0.0.1 5432 && nc -vz -w 3 192.168.88.11 5432'
```

正常预期：

- 四条都成功

如果失败：

- 先看 APISIX 端口是否监听
- 再看容器端口是否发布

### 7.4 验证 MySQL stream 是否真的到达 MySQL

```bash
python3 - <<'PY'
import socket
for host, port, label in [("192.168.88.17",3306,"direct"),("192.168.88.11",3306,"apisix")]:
    s = socket.create_connection((host, port), timeout=5)
    data = s.recv(16)
    s.close()
    print(f"{label}: {data.hex()} | {data!r}")
PY
```

正常预期：

- 直接连 `192.168.88.17:3306` 能读到 MySQL 握手字节
- 通过 `apisix.tail5e888.ts.net:3306` 也能读到 MySQL 握手字节
- 两边都能看到 MySQL `8.4.8` 协议特征

若 APISIX 端没有握手，而直连有：

- APISIX MySQL stream 配置或 stream_route 失效

若两边都没有握手：

- 优先怀疑 MySQL 宿主机或 MySQL 容器问题

### 7.5 验证 PostgreSQL stream 是否真的到达 PostgreSQL

```bash
PGPASSWORD='<POSTGRES_PASSWORD>' psql \
  -h apisix.tail5e888.ts.net \
  -p 5432 \
  -U <POSTGRES_USER> \
  -d <POSTGRES_DB> \
  -At -c 'select current_user, current_database();'
```

```bash
PGPASSWORD='<POSTGRES_PASSWORD>' psql \
  -h 192.168.88.16 \
  -p 5432 \
  -U <POSTGRES_USER> \
  -d <POSTGRES_DB> \
  -At -c 'select current_user, current_database();'
```

正常预期：

- 通过 `apisix.tail5e888.ts.net:5432` 能成功返回 `current_user,current_database`
- 直连 `192.168.88.16:5432` 的结果与 APISIX 路径一致

若 APISIX 路径失败而直连成功：

- APISIX PostgreSQL stream 配置或 stream_route 失效

若两边都失败：

- 优先怀疑 PostgreSQL 账号权限、数据库状态或宿主机网络

### 7.6 检查 MySQL / PostgreSQL 上游宿主机前提

在 MySQL 宿主机执行：

```bash
ssh ubuntu@192.168.88.17 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

```bash
ssh ubuntu@192.168.88.17 'ss -lntp | grep 3306 || true'
```

```bash
ssh ubuntu@192.168.88.17 'sudo docker port mysql-01'
```

在 PostgreSQL / Supabase 宿主机执行：

```bash
ssh ubuntu@192.168.88.16 'ss -lntp | grep 5432 || true'
```

正常预期：

- `mysql-01` 容器在运行
- `3306:3306` 已发布
- MySQL 宿主机监听 `0.0.0.0:3306`
- PostgreSQL 宿主机监听 `0.0.0.0:5432` 或进程级等效监听

---

## 8. 常见故障与对应定位

### 8.1 现象：`/supabase/*` 变成 404/401/502

优先检查：

1. `supabase-route-http-v2` 是否存在
2. `priority` 是否仍为 `10`
3. `supabase_client_v1` 是否存在
4. `supabase-gateway-http-v1` 是否仍指向 `192.168.88.16:8000`

### 8.2 现象：不带 APISIX key 也能访问 `/supabase/*`

这通常意味着：

- v2 route 被删了
- v1 route 在单独生效
- 或者有更高优先级的同路径 route 覆盖了 v2

### 8.3 现象：带 APISIX key 访问 `/supabase/*` 仍 401

优先检查：

- Consumer 是否存在
- route 中的 `key-auth` 是否还在
- `proxy-rewrite.headers.set` 是否还在
- 上游 `192.168.88.16:8000` 是否可达

### 8.4 现象：`3306` 端口在，但数据库客户端连不上

优先检查：

- `stream_route` 是否仍在
- 是否能读取 MySQL 握手包
- `192.168.88.17:3306` 直连是否仍正常

### 8.5 现象：`5432` 端口在，但数据库客户端连不上

优先检查：

- `postgres-stream-5432-v1` 是否仍在
- 通过 `apisix.tail5e888.ts.net:5432` 的 `psql` 是否成功
- `192.168.88.16:5432` 直连是否仍正常

### 8.6 现象：启用 stream 后 HTTP 路由异常

优先检查：

- `config.yaml` 是否误把 `proxy_mode` 改成了纯 `stream`
- `docker-compose.yml` 是否误删了 `9080/9180/9443`
- APISIX 重建后 `supabase-route-http-v2` 是否仍可回读

---

## 9. 配置文件与对象真源

### 9.1 APISIX 主机配置文件

| 文件 | 用途 |
|---|---|
| `/opt/apisix-gw-test-01/config.yaml` | APISIX 主配置 |
| `/opt/apisix-gw-test-01/docker-compose.yml` | APISIX 容器端口与挂载 |

### 9.2 当前关键 Admin API 对象

| 对象 | 当前用途 |
|---|---|
| `supabase-gateway-http-v1` | Supabase HTTP 上游 |
| `supabase-route-http-v1` | Supabase 旧版纯转发 |
| `supabase-route-http-v2` | Supabase 当前生效入口 |
| `supabase_client_v1` | Supabase HTTP 客户端业务 key 绑定 |
| `mysql-stream-3306-v1` | MySQL stream 入口 |
| `postgres-stream-5432-v1` | PostgreSQL stream 入口 |

### 9.3 凭据存放边界

凭据不写入仓库文档正文，只说明位置类别：

| 凭据 | 存放位置 |
|---|---|
| APISIX Admin Key | 1Password |
| APISIX 客户端业务 key | 1Password |
| Supabase Anon Key | APISIX route 配置 + 安全存储 |

---

## 10. 变更后第一响应建议

出现问题时，建议按照下面顺序处理：

1. 先看 APISIX 容器和监听端口
2. 再查 Admin API 对象是否还在
3. 然后分流：
   - HTTP 问题走 Supabase route / upstream 检查
   - MySQL TCP 问题走 stream_route / MySQL 握手检查
   - PostgreSQL TCP 问题走 stream_route / `psql` 对照检查
4. 如果是配置变更后出现问题：
   - 优先对照备份文件恢复
   - 再重建 APISIX

这样做可以最快把问题定位到：

- 宿主机/容器层
- APISIX 配置层
- 路由对象层
- 上游服务层

---

## 11. 术语说明

| 术语 | 含义 |
|---|---|
| APISIX Admin Key | 用于调用 `9180` Admin API 的管理密钥 |
| APISIX 业务 key | 客户端访问 `/supabase/*` 时提交给 APISIX 的入口凭据 |
| Supabase Anon Key | APISIX 自动注入给 Supabase gateway 的上游业务 key |
| stream_route | APISIX 用于 TCP/UDP 代理的路由对象 |
| MySQL 握手包 | 客户端与 MySQL 建立连接时最先收到的协议头，可用于判断链路是否真的到达 MySQL |
