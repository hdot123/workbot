---
type: [KB:LESSON]
title: S-UI (Sing-Box UI) 部署文档
created: 2026-03-05
updated: 2026-03-05
source: Manual
confidence: high
tags: [s-ui, sing-box, proxy, 通用]
status: active
last_verified: 2026-03-05
applicable: [node-00, node-11, node-22, 所有 Linux 服务器]
version: v1.0
related: []
---

# S-UI (Sing-Box UI) 部署文档

> S-UI 是一个基于 Sing-Box 的代理管理面板，支持多种协议（VMess、VLESS、Hysteria2、Trojan 等）

---

## 快速访问

| 服务器 | Tailscale IP | 面板地址 | 状态 |
|--------|-------------|----------|------|
| **node-22** | 100.100.1.22 | `https://100.100.1.22:2095` | ✅ 运行中 |

---

## 安装步骤

### 1. 一键安装

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/alireza0/s-ui/main/install.sh)
```

### 2. 安装后自动显示

- Web 面板地址
- 用户名/密码
- 订阅地址

---

## 管理命令

```bash
# 查看状态
s-ui status

# 启动/停止/重启
s-ui start
s-ui stop
s-ui restart

# 查看日志
s-ui log

# 设置管理员凭据
s-ui 6

# 查看管理员凭据
s-ui 7

# 修改面板设置
s-ui 9

# 卸载
s-ui uninstall
```

---

## 端口说明

| 端口 | 用途 | 访问方式 |
|------|------|----------|
| **2095** | Web 管理面板 | Tailscale 内网 |
| **18422** | 订阅服务器 | Tailscale/公网 |
| **52564** | VMess 入站 | 公网 |
| **20892** | VMess 入站 | 公网 |

---

## 安全建议

### 1. 仅允许 Tailscale 访问面板

修改面板监听地址为 Tailscale IP：
```bash
s-ui 9  # 设置面板监听地址为 100.100.1.22
```

### 2. 使用强密码

```bash
s-ui 6  # 设置管理员凭据
```

### 3. 配置 SSL 证书

使用 Let's Encrypt 证书（见 `ssl-certificate-deployment.md`）

---

## 各服务器部署记录

| 服务器 | 部署日期 | 面板端口 | 状态 | 备注 |
|--------|----------|----------|------|------|
| **node-22** | 2026-03-05 | 2095 | ✅ 运行 | Tailscale 访问 |
| **node-00** | - | - | ⏳ 待部署 | - |
| **node-11** | - | - | ⏳ 待部署 | 内网服务器 |

---

## 常用操作

### 添加入站（Inbound）

1. 登录面板 `https://100.100.1.22:2095`
2. 进入 **Inbounds** → **Add Inbound**
3. 选择协议（VMess/VLESS/Hysteria2/Trojan）
4. 配置端口、UUID、加密方式
5. 保存后生成订阅链接

### 配置客户端（Mihomo）

在 Mihomo 配置中添加：

```yaml
proxies:
  - name: node-22-vmess
    type: vmess
    server: 100.100.1.22
    port: 52564
    uuid: your-uuid-here
    alterId: 0
    cipher: auto
    udp: true
    tls: false
```

### 订阅链接

格式：`https://100.100.1.22:18422/sub/YOUR_SUBSCRIPTION_ID`

---

## 故障排查

### 面板无法访问

```bash
# 检查服务状态
s-ui status

# 检查端口监听
netstat -tlnp | grep 2095

# 检查防火墙
iptables -L INPUT -n | grep 2095
```

### 客户端连不上

1. 确认入站端口已开放（阿里云安全组）
2. 确认 Sing-Box 服务正常 `s-ui status`
3. 检查客户端配置（UUID、端口、协议）

---

## S-UI 中转配置（高级）

S-UI 可以作为代理中转节点，将外部订阅链接的节点通过 S-UI 的入站协议（VMess/VLESS 等）转发给客户端使用。

### 架构说明

```
客户端 (Mihomo) → S-UI 入站 → S-UI 出站 (外部订阅) → 目标服务器
```

### 配置步骤

#### 1. 添加外部订阅到 outbounds

通过 Python 脚本从订阅链接提取节点并添加到 outbounds 表：

```python
#!/usr/bin/env python3
import sqlite3
import json
import requests
import base64

# 获取订阅内容
url = "https://subscription-url/?token=xxx"
response = requests.get(url, verify=False)
data = base64.b64decode(response.text).decode('utf-8')
links = data.strip().split('\n')

# 连接数据库
conn = sqlite3.connect('/usr/local/s-ui/db/s-ui.db')
cursor = conn.cursor()

# 解析每个链接并插入 outbounds 表
for link in links:
    # 使用 util.GetOutbound() 解析链接
    # 或直接构造 sing-box 配置
    config = {...}  # sing-box outbound 配置
    options = json.dumps(config, indent=2).encode('utf-8')
    cursor.execute(
        "INSERT INTO outbounds (type, tag, options) VALUES (?, ?, ?)",
        (link_type, tag, options)
    )

conn.commit()
conn.close()
```

#### 2. 创建代理组（Selector）

```python
# 创建 selector 代理组
selector_config = {
    "type": "selector",
    "tag": "Proxy",
    "outbounds": ["node-01", "node-02", ...],
    "default": "node-01"
}
options = json.dumps(selector_config, indent=2).encode('utf-8')
cursor.execute(
    "INSERT INTO outbounds (type, tag, options) VALUES (?, ?, ?)",
    ("selector", "Proxy", options)
)
```

#### 3. 配置路由规则

修改 `settings.config` 中的路由规则：

```json
{
  "route": {
    "rules": [
      {"action": "sniff"},
      {"protocol": ["dns"], "action": "hijack-dns"}
    ]
  }
}
```

#### 4. 重启 S-UI

```bash
s-ui restart
```

### 注意事项

1. **VLESS Reality 节点**需要配置 uTLS 指纹：
   ```json
   {
     "tls": {
       "enabled": true,
       "reality": {...},
       "utls": {
         "enabled": true,
         "fingerprint": "chrome"
       }
     }
   }
   ```

2. **outbounds.options 字段**必须是 BLOB 格式（UTF-8 编码的 JSON）

3. **代理组类型**：
   - `selector`: 手动选择或自动测试
   - `urltest`: 自动选择延迟最低的节点

### 故障排查

1. **SQL Scan 错误**：确保 options 字段是 BLOB 格式，不是 TEXT
2. **uTLS 错误**：Reality 节点必须配置 uTLS 指纹
3. **入站未启动**：检查 `s-ui log` 中的 sing-box 启动日志

---

**文档版本**: v1.1
**最后更新**: 2026-03-05
**适用范围**: 所有 Linux 服务器
