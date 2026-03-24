# node-11 多租客 OpenClaw 环境部署文档

**部署日期**: 2026-02-28
**服务器**: node-11 (100.100.1.11)
**系统**: Debian 13 (trixie)
**硬件**: 11GB RAM

---

## 📋 系统架构

```
┌─────────────┐
│   客户端     │
│  (浏览器)    │
└──────┬──────┘
       │ HTTPS (Tailscale证书)
       ↓
┌─────────────────────────────────────────┐
│           Caddy 反向代理                 │
│  监听: 18810, 18820, 18830              │
│  域名: node-11.tail5e888.ts.net          │
└──────┬──────────────────────────────────┘
       │ HTTP (本地回环)
       ↓
┌─────────────────────────────────────────┐
│       OpenClaw 网关 (多租客)             │
│  user1: 19010  user2: 19050  user3: 19090│
│  bind: lan                               │
└─────────────────────────────────────────┘
```

---

## 🏗️ 租户配置

### user1 (租客1)

**OpenClaw配置**:
- **端口**: 19010
- **绑定**: lan
- **令牌**: `user1-exclusive-token-19010`
- **配置文件**: `/home/user1/.openclaw/openclaw.json`

**Caddy配置**:
- **监听端口**: 18810
- **转发目标**: 127.0.0.1:19010
- **访问地址**: `https://node-11.tail5e888.ts.net:18810/`

### user2 (租客2)

**OpenClaw配置**:
- **端口**: 19050
- **绑定**: lan
- **令牌**: `user2-exclusive-token-19050`
- **配置文件**: `/home/user2/.openclaw/openclaw.json`

**Caddy配置**:
- **监听端口**: 18820
- **转发目标**: 127.0.0.1:19050
- **访问地址**: `https://node-11.tail5e888.ts.net:18820/`

### user3 (租客3)

**OpenClaw配置**:
- **端口**: 19090
- **绑定**: lan
- **令牌**: `user3-exclusive-token-19090`
- **配置文件**: `/home/user3/.openclaw/openclaw.json`

**Caddy配置**:
- **监听端口**: 18830
- **转发目标**: 127.0.0.1:19090
- **访问地址**: `https://node-11.tail5e888.ts.net:18830/`

---

## 🔧 配置文件示例

### OpenClaw 配置 (`/home/user1/.openclaw/openclaw.json`)

```json
{
  "gateway": {
    "port": 19010,
    "mode": "local",
    "bind": "lan",
    "controlUi": {
      "dangerouslyAllowHostHeaderOriginFallback": true
    },
    "auth": {
      "mode": "token",
      "token": "user1-exclusive-token-19010"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-5"
      }
    }
  }
}
```

### Caddy 配置 (`/etc/caddy/Caddyfile`)

```caddy
node-11.tail5e888.ts.net:18810 {
    reverse_proxy 127.0.0.1:19010
}

node-11.tail5e888.ts.net:18820 {
    reverse_proxy 127.0.0.1:19050
}

node-11.tail5e888.ts.net:18830 {
    reverse_proxy 127.0.0.1:19090
}
```

---

## 📝 部署步骤

### 1. 安装 Mise (Node.js 版本管理器)

```bash
# 安装 Mise
curl https://mise.run | sh

# 添加到 PATH
echo 'export PATH="$HOME/.local/share/mise/bin:$PATH"' >> ~/.profile
source ~/.profile

# 安装 Node.js 22
mise install node@22.22.0
mise use --global node@22.22.0
```

### 2. 安装 OpenClaw

```bash
# 安装 OpenClaw
npm install -g openclaw-cli

# 验证安装
openclaw --version
```

### 3. 创建用户

```bash
# 创建用户
useradd -m -s /bin/bash user1
useradd -m -s /bin/bash user2
useradd -m -s /bin/bash user3

# 设置密码（可选）
echo "user1:password" | chpasswd
echo "user2:password" | chpasswd
echo "user3:password" | chpasswd
```

### 4. 配置 OpenClaw

```bash
# 为每个用户创建配置
mkdir -p /home/user1/.openclaw
mkdir -p /home/user2/.openclaw
mkdir -p /home/user3/.openclaw

# 创建配置文件 (参考上面的配置文件示例)
# ...

# 设置权限
chown -R user1:user1 /home/user1/.openclaw
chown -R user2:user2 /home/user2/.openclaw
chown -R user3:user3 /home/user3/.openclaw
```

### 5. 配置 PM2 (进程管理)

```bash
# 为每个用户安装 PM2
su - user1 -c "npm install -g pm2"
su - user2 -c "npm install -g pm2"
su - user3 -c "npm install -g pm2"

# 启动 OpenClaw 网关
su - user1 -c "cd /home/user1/.openclaw && pm2 start 'openclaw gateway' --name openclaw-gateway"
su - user2 -c "cd /home/user2/.openclaw && pm2 start 'openclaw gateway' --name openclaw-gateway"
su - user3 -c "cd /home/user3/.openclaw && pm2 start 'openclaw gateway' --name openclaw-gateway"

# 保存 PM2 配置
su - user1 -c "pm2 save"
su - user2 -c "pm2 save"
su - user3 -c "pm2 save"
```

### 6. 安装 Caddy

```bash
# 添加 Caddy 源
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list

# 安装 Caddy
apt update
apt install -y caddy

# 配置 Caddyfile (参考上面的配置文件示例)
# ...

# 启动 Caddy
systemctl start caddy
systemctl enable caddy
```

### 7. 配置 Tailscale

```bash
# 启动 Tailscale
systemctl start tailscaled
systemctl enable tailscaled

# 为 Caddy 配置 Tailscale operator 权限
tailscale set --operator=caddy

# 重启 Caddy
systemctl restart caddy
```

### 8. 设备配对

```bash
# 列出待批准的设备
su - user1 -c "openclaw devices list"

# 批准设备
su - user1 -c "openclaw devices approve <requestId>"
```

---

## 🌐 访问方式

### HTTPS 访问 (推荐)

**访问地址**：
- **user1**: `https://node-11.tail5e888.ts.net:18810/`
- **user2**: `https://node-11.tail5e888.ts.net:18820/`
- **user3**: `https://node-11.tail5e888.ts.net:18830/`

**使用令牌**：
```
https://node-11.tail5e888.ts.net:18810/?token=user1-exclusive-token-19010
```

### HTTP 访问 (局域网)

**注意**：HTTP 访问会触发浏览器的安全限制，需要额外配置。

**访问地址**：
- **user1**: `http://192.168.88.81:19010/`
- **user2**: `http://192.168.88.81:19050/`
- **user3**: `http://192.168.88.81:19090/`

**如果需要HTTP访问，需要添加以下配置**：
```json
"controlUi": {
  "dangerouslyDisableDeviceAuth": true
}
```

---

## 🔑 网关令牌

| 用户 | 令牌 |
|------|------|
| user1 | `user1-exclusive-token-19010` |
| user2 | `user2-exclusive-token-19050` |
| user3 | `user3-exclusive-token-19090` |

**使用方式**：
```
https://node-11.tail5e888.ts.net:18810/?token=user1-exclusive-token-19010
```

---

## 🚨 故障排除

### 1. 网关无法启动

**错误信息**：
```
Gateway failed to start: Error: non-loopback Control UI requires gateway.controlUi.allowedOrigins
```

**解决方案**：
在配置文件中添加：
```json
"controlUi": {
  "dangerouslyAllowHostHeaderOriginFallback": true
}
```

### 2. SSL 证书错误

**错误信息**：
```
ERR_SSL_PROTOCOL_ERROR
```

**解决方案**：
```bash
# 重新配置 Tailscale operator 权限
tailscale set --operator=caddy

# 重启 Caddy
systemctl restart caddy
```

### 3. 设备需要配对

**错误信息**：
```
pairing required
此设备需要网关主机的配对批准。
```

**解决方案**：
```bash
# 列出待批准的设备
su - user1 -c "openclaw devices list"

# 批准设备
su - user1 -c "openclaw devices approve <requestId>"
```

### 4. 端口被占用

**错误信息**：
```
listen tcp :18810: bind: address already in use
```

**解决方案**：
```bash
# 检查端口占用
lsof -i :18810

# 杀掉占用端口的进程
kill -9 <PID>
```

---

## 📚 经验教训

### 1. 配置问题

**问题**：OpenClay 网关无法启动，报错 "non-loopback Control UI requires gateway.controlUi.allowedOrigins"

**原因**：当 `bind: "lan"` 时，OpenClaw 需要配置 `dangerouslyAllowHostHeaderOriginFallback: true`

**解决方案**：在配置文件中添加 `controlUi` 配置

### 2. 证书问题

**问题**：浏览器访问时出现 `ERR_SSL_PROTOCOL_ERROR`

**原因**：Caddy 无法从 Tailscale 获取证书，报错 "Access denied: cert access denied"

**解决方案**：为 Caddy 配置 Tailscale operator 权限：`tailscale set --operator=caddy`

### 3. 设备配对问题

**问题**：浏览器访问时显示 "pairing required"

**原因**：OpenClaw 的设备需要手动批准

**解决方案**：使用 `openclaw devices approve <requestId>` 批准设备

### 4. HTTP 访问限制

**问题**：使用局域网 IP (HTTP) 访问时，浏览器会阻止设备身份生成

**原因**：浏览器的 WebCrypto API 只能在 HTTPS 或 127.0.0.1 下使用

**解决方案**：
1. 使用 HTTPS (推荐)
2. 或添加 `dangerouslyDisableDeviceAuth: true` 配置（不推荐）

### 5. Caddy 配置问题

**问题**：Caddy 只监听 Tailscale 域名，不监听局域网 IP

**原因**：Caddyfile 配置中指定了域名：`node-11.tail5e888.ts.net:18810`

**解决方案**：
1. 使用 Tailscale 域名访问（推荐）
2. 或修改 Caddyfile 为 `:18810`（监听所有接口）

---

## 🔧 维护命令

### 检查服务状态

```bash
# 检查 Caddy 状态
systemctl status caddy

# 检查 OpenClaw 网关状态
su - user1 -c "pm2 status"

# 检查 Tailscale 状态
systemctl status tailscaled

# 检查端口监听
lsof -i :18810 -i :18820 -i :18830
lsof -i :19010 -i :19050 -i :19090
```

### 重启服务

```bash
# 重启 Caddy
systemctl restart caddy

# 重启 OpenClaw 网关
su - user1 -c "pm2 restart openclaw-gateway"
su - user2 -c "pm2 restart openclaw-gateway"
su - user3 -c "pm2 restart openclaw-gateway"

# 重启 Tailscale
systemctl restart tailscaled
```

### 查看日志

```bash
# 查看 Caddy 日志
journalctl -u caddy.service -f

# 查看 OpenClaw 网关日志
su - user1 -c "pm2 logs openclaw-gateway"
```

---

## 📊 资源使用

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Caddy (user1) | 18810 | HTTPS 代理 |
| Caddy (user2) | 18820 | HTTPS 代理 |
| Caddy (user3) | 18830 | HTTPS 代理 |
| OpenClaw (user1) | 19010 | 网关 |
| OpenClaw (user2) | 19050 | 网关 |
| OpenClaw (user3) | 19090 | 网关 |

### 系统要求

- **操作系统**: Debian 13 (trixie) 或更高版本
- **内存**: 至少 11GB RAM
- **磁盘**: 至少 20GB 可用空间
- **网络**: Tailscale 网络连接

---

## 🔐 安全建议

1. **使用 HTTPS**：始终使用 HTTPS 访问，避免使用 HTTP
2. **定期更新令牌**：定期更换网关令牌
3. **限制访问**：使用防火墙限制不必要的端口访问
4. **监控日志**：定期检查日志，发现异常及时处理
5. **备份数据**：定期备份配置文件和重要数据

---

**文档版本**: 1.0
**最后更新**: 2026-02-28
**维护者**: Molt (战术蟹王)
