---
type: [KB:PROJECT]
title: node-22 东京服务器
created: 2026-03-02
tags: [server, tokyo, node-22, tailscale, x-ui, vless, gost, proxy]
source: Manual
confidence: high
status: active
last_verified: 2026-03-12
version: v2.1
related: [ct110, pve, node-11, clawrouter]
updated: 2026-03-12
---

# node-22 东京服务器

## 基本信息

### 服务器标识
- **主机名**: node-22
- **SSH 别名**: node-22
- **位置**: 东京
- **提供商**: 阿里云

### 访问信息
- **外网 IPv4**: `43.167.177.86`
- **内网 IPv4**: `10.7.0.8/22`（阿里云内网）
- **外网 IPv6**: 无
- **SSH 访问**: `ssh node-22`（root 用户）

### 系统信息
- **操作系统**: OpenCloudOS 9.4
- **内核版本**: 6.6.117-45.1.oc9.x86_64
- **原始主机名**: VM-0-8-opencloudos

## 网络配置

### 物理网卡（eth0）
- **IPv4**: `10.7.0.8/22`（阿里云内网地址）
- **IPv6**: `fe80::9291:4502:d778:6956/64`（链路本地地址）

### Tailscale 虚拟网卡（tailscale0）
- **IPv4**: `100.100.1.22/32`（Tailscale 内网地址）
- **IPv6**: `fd7a:115c:a1e0::938:26/128`（Tailscale 内网地址）
- **DNS 名称**: `node-22.tail5e888.ts.net`
- **状态**: Running（已连接）

### 外网访问
- **公网 IPv4**: `43.167.177.86`
- **公网 IPv6**: 无（不支持外网 IPv6）

### S-UI (Sing-Box UI)
- **状态**: ❌ 已卸载
- **说明**: 已改用 x-ui (Xray 管理面板)

### x-ui (Xray 管理面板)
- **状态**: ✅ 运行中
- **安装路径**: `/etc/x-ui/`
- **数据库**: `/etc/x-ui/x-ui.db`
- **管理命令**: `x-ui`
- **内网访问**: `https://node-22.tail5e888.ts.net:25432/P0XVBQ3z9Q37TddAr0/` (需 Tailscale)
- **订阅地址**: `https://ai.qqbaidu.de5.net:2096/sub/xxx` (公网)

### VLESS Reality 入站配置 (2026-03-06 测试最优)

| 参数 | 443 节点 (主用) | 5443 节点 (备用) |
|------|----------------|----------------|
| **端口** | 443 | 5443 |
| **协议** | vless | vless |
| **UUID** | `DC995EC2-24DB-288D-B65B-F1DA779F6161` | `03338bb7-8ae7-4c8d-8999-09216eb01e9b` |
| **flow** | `xtls-rprx-vision` | `xtls-rprx-vision` |
| **network** | `tcp` | `tcp` |
| **security** | `reality` | `reality` |
| **Reality Target** | `www.microsoft.com:443` | `www.apple.com:443` |
| **serverNames** | `microsoft.com`, `www.microsoft.com` | `apple.com`, `www.apple.com` |
| **privateKey** | `eJnlHpkWQrZyZNtbFNwFuzusZAOJGj_lUvJnU6H5OGQ` | `eJnlHpkWQrZyZNtbFNwFuzusZAOJGj_lUvJnU6H5OGQ` |
| **publicKey** | `TL2o8loc9qzpRhvLTbyMbx0MKubIanXnxDCREmszBFc` | `TL2o8loc9qzpRhvLTbyMbx0MKubIanXnxDCREmszBFc` |
| **shortId** | `0959cb6e0a2618cd` (推荐) | `223a797b16` (推荐) |
| **fingerprint** | `chrome` | `chrome` |

### 订阅链接

| 用途 | 订阅地址 | 访问方式 |
|------|---------|---------|
| **主用 (443)** | `https://ai.qqbaidu.de5.net:2096/sub/xxx?insert=443` | 公网 |
| **备用 (5443)** | `https://ai.qqbaidu.de5.net:2096/sub/xxx?insert=5443` | 公网 |
| **内网订阅** | `https://node-22.tail5e888.ts.net:25432/sub/xxx` | Tailscale |

### 其他入站端口

| 端口 | 协议 | 说明 | 状态 |
|------|------|------|------|
| 52564 | VMess+WS+TLS | 旧 S-UI 配置 | ⚠️ 保留 |
| 20892 | VMess+Reality | 旧 S-UI 配置 | ⚠️ 保留 |
| 9443 | xray | 监听中 | ❌ 测试无效 (无真实命中流量) |
| 8443 | XHTTP | 测试配置 | ❌ 测试无效 (无真实命中流量) |

> **注意**: 8443/9443 端口测试无效，原因是未真实命中入站流量，不代表协议本身不可用。

### 客户端配置模板 (Mihomo)

```yaml
- name: "N22-443-TCP-Vision"
  type: vless
  server: 43.167.177.86
  port: 443
  uuid: DC995EC2-24DB-288D-B65B-F1DA779F6161
  network: tcp
  tls: true
  udp: true
  packet-encoding: xudp
  flow: xtls-rprx-vision
  client-fingerprint: chrome
  reality-opts:
    public-key: TL2o8loc9qzpRhvLTbyMbx0MKubIanXnxDCREmszBFc
    short-id: 0959cb6e0a2618cd
  servername: www.microsoft.com
```

### 常用命令

```bash
# x-ui 管理
x-ui                       # 控制面板
x-ui restart               # 重启服务
x-ui log                   # 查看日志

# 查看入站配置
sqlite3 /etc/x-ui/x-ui.db "SELECT id, port, protocol, remark FROM inbounds;"

# 检查端口监听
netstat -tlnp | grep -E '443|5443|8443|9443'
```

## 已安装软件

### Tailscale
- **版本**: v1.76.6
- **安装方式**: 静态二进制文件
- **安装路径**: `/usr/bin/tailscale`, `/usr/bin/tailscaled`
- **守护进程**: PID 17223（运行中）
- **连接状态**: 已连接到 Tailscale 网络

### OpenClaw
- **配置目录**: `/root/.openclaw/`
- **配置文件**: `/root/.openclaw/openclaw.json`
- **Gateway 端口**: 18789（默认）
- **Tailscale 访问**: `http://node-22.tail5e888.ts.net:18789`
- **远程 CLI**: `openclaw --url http://node-22.tail5e888.ts.net:18789 --token <token>`

### GOST v3 代理服务
- **版本**: v3.2.7
- **安装路径**: `/usr/local/bin/gost`
- **配置文件**: `/etc/gost/gost.yaml`
- **Systemd 服务**: `/etc/systemd/system/gost.service`
- **服务状态**: ✅ 运行中，已启用开机自启
- **管理命令**:
  ```bash
  sudo systemctl status gost    # 查看状态
  sudo systemctl restart gost   # 重启服务
  sudo journalctl -u gost -f    # 查看日志
  ```

#### 端口配置

| 端口 | 协议 | 监听地址 | 用途 | 访问范围 |
|------|------|---------|------|---------|
| **18443** | Shadowsocks | `0.0.0.0:18443` | 公网隧道入口 | 公网 |
| **18081** | SOCKS5 | `100.100.1.22:18081` | 内网通用代理 | Tailscale |
| **18082** | HTTP | `100.100.1.22:18082` | Docker 镜像拉取 | Tailscale |
| **1082** | HTTP | `100.100.1.22:1082` | Voyage 专用代理 | Tailscale |
| **18080** | HTTP API | `100.100.1.22:18080` | GOST 管理接口 | Tailscale |

#### 配置文件示例

**`/etc/gost/gost.yaml`**:
```yaml
services:
  # 1. 公网 Shadowsocks 入口 (18443)
  - name: "fast-ss-tunnel"
    addr: ":18443"
    handler:
      type: "ss"
      auth:
        username: "chacha20-ietf-poly1305"
        password: "chacha20-ietf-poly1305"
    listener:
      type: "tcp"

  # 2. Tailscale SOCKS5 代理 (18081)
  - name: "internal-socks5"
    addr: "100.100.1.22:18081"
    handler:
      type: "socks5"
    listener:
      type: "tcp"

  # 3. Tailscale HTTP 代理 (18082，Docker 拉取镜像)
  - name: "internal-http-proxy"
    addr: "100.100.1.22:18082"
    handler:
      type: "http"
    listener:
      type: "tcp"

  # 4. Tailscale HTTP 代理 (1082，Voyage 专用)
  - name: "voyage-proxy"
    addr: "100.100.1.22:1082"
    handler:
      type: "http"
    listener:
      type: "tcp"

# API 管理接口
api:
  addr: "100.100.1.22:18080"
  pathPrefix: "/api"
  auth:
    username: "admin"
    password: "admin"
```

**`/etc/systemd/system/gost.service`**:
```ini
[Unit]
Description=GOST Service on Tokyo Node
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/gost -C /etc/gost/gost.yaml
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

#### 使用场景

1. **Voyage API 代理** (ClawRouter VM → node-22:1082)
   - ClawRouter 通过 `socks5://100.100.1.22:18081` 访问 Voyage API
   - 避免 Voyage API 直连国内网络不稳定的问题

2. **Docker 镜像拉取** (内网服务器 → node-22:18082)
   - 配置 Docker daemon 使用 HTTP 代理
   - 加速国外镜像拉取

3. **内网通用代理** (Tailscale 设备 → node-22:18081)
   - SOCKS5 协议，兼容性好
   - 用于需要代理的应用程序

#### 验证命令

```bash
# 测试 SOCKS5 代理
curl -s -m 5 -x socks5://100.100.1.22:18081 http://www.google.com > /dev/null && echo "SOCKS5 OK" || echo "SOCKS5 FAIL"

# 测试 HTTP 代理
curl -s -m 5 -x http://100.100.1.22:1082 http://www.google.com > /dev/null && echo "HTTP OK" || echo "HTTP FAIL"

# 查看连接数
netstat -an | grep :18081 | grep ESTABLISHED | wc -l

# 查看实时日志
sudo journalctl -u gost -f
```

#### 相关文档
- **Voyage 代理配置**: `workspace/projects/voyage-proxy-config-2026-03-12.md`
- **ClawRouter 文档**: `workspace/memory/kb/projects/clawrouter-vm101.md`

## 部署历史

### 2026-03-02 — Tailscale 部署
1. **安装 Tailscale v1.76.6**
   - 下载静态二进制文件（因为 OpenCloudOS 不被自动识别）
   - 安装到 `/usr/bin/`
   
2. **修改主机名**
   - 原主机名：`VM-0-8-opencloudos`
   - 新主机名：`node-22`
   - 更新 `/etc/hosts` 文件

3. **启动 Tailscale**
   - 启动 tailscaled 守护进程
   - 执行 `tailscale up` 连接
   - 浏览器认证完成
   - 状态：Running

## 注意事项
 
### 网络限制
- 无外网 IPv6 支持
- 外网访问仅支持 IPv4
 
### Tailscale 配置
- 使用静态二进制文件安装（标准安装脚本不支持 OpenCloudOS）
- 守护进程需要手动启动（未配置 systemd 服务）
 
### 排障记录 (Troubleshooting)
- **[2026-03-07] x-ui 端口冲突宕机恢复**:
  - **问题现象**: `x-ui` 服务宕机（无法启动），面板端口 25432 无法访问。`journalctl -u x-ui` 显示报错 `listen tcp :25432: bind: address already in use`。
  - **根本原因**: 之前调试 Tailscale Funnel / Serve 时，将内部的 `tailscale serve` 绑定到了 `25432` 端口（代理到后端的 127.0.0.1:25432）。但是由于 x-ui 本身需要监听 `[::]:25432`，导致 Tailscale 的代理强占了 x-ui 面板入口。
  - **解决办法**: 执行 `tailscale serve reset` 清理错误的端口占用，随后 `systemctl restart x-ui`。节点全线恢复正常。
 
---

## 相关服务器

- **node-00**: 47.111.21.195（阿里云主节点）
- **node-01**: 116.62.168.71（阿里云从节点）
- **node-11**: 192.168.88.30（局域网节点，Ubuntu 24.04）

---

## 更新历史

- **2026-03-12 14:00**: GOST v3.2.7 代理服务部署完成
  - 配置 5 个代理端口（18443, 18081, 18082, 1082, 18080）
  - 启用 systemd 服务，配置开机自启
  - ClawRouter Voyage 专用代理已切换到 SOCKS5（`socks5://100.100.1.22:18081`）
  - 文档：`workspace/projects/voyage-proxy-config-2026-03-12.md`
- **2026-03-06 12:00**: x-ui 分阶段部署 - Step 1 完成
  - 添加 5 个 outbound (2 HK VLESS + 1 SS + 2 JP VLESS)
  - 组映射：out-video (2), out-openai (2), out-gemini (1), out-search (2)
  - 文档：`workspace/projects/node-22-x-ui-step1-manual-guide.md`
  - 脚本：`workspace/projects/node-22-x-ui-deploy-step1.sh`
- **2026-03-06 11:00**: x-ui tailscale serve 配置完成
  - `https://node-22.tail5e888.ts.net:25432/P0XVBQ3z9Q37TddAr0/`
- **2026-03-06**: 完成 VLESS Reality 节点测试 (443/5443)，记录最优配置到文档
  - 主用推荐：443 端口 (www.microsoft.com Reality)
  - 备用推荐：5443 端口 (www.apple.com Reality)
- **2026-03-04**: S-UI 已卸载，改用 x-ui
- **2026-03-02**: Tailscale 部署完成

---

**文档创建时间**: 2026-03-02 19:00
**创建者**: Molt 国王
