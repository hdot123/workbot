---
type: [KB:GLOBAL]
title: SSL 证书申请与部署（Let's Encrypt）
created: 2026-03-05
updated: 2026-03-05
source: Manual
confidence: high
tags: [ssl, letsencrypt, acme.sh, certificate, 通用]
status: active
last_verified: 2026-03-05
applicable: [node-00, node-11, node-22, 所有 Linux 服务器]
version: v1.0
related: []
---

# SSL 证书申请与部署（Let's Encrypt）

> 通用文档：适用于所有 Linux 服务器

---

## 通用签发步骤

### 1. 安装 acme.sh

```bash
curl -fsSL https://get.acme.sh | sh
source ~/.bashrc
```

### 2. 注册账户

```bash
~/.acme.sh/acme.sh --register -m huhuun17@gmail.com
```

### 3. 签发证书（HTTP 验证）

**前提条件**：
- 阿里云安全组放行 TCP 80 端口
- 域名解析指向服务器 IP（关闭 Cloudflare 代理）

```bash
~/.acme.sh/acme.sh --issue -d <你的域名> --standalone --server letsencrypt -m huhuun17@gmail.com --force
```

### 4. 安装证书

```bash
~/.acme.sh/acme.sh --install-cert -d <你的域名> --ecc \
  --key-file /etc/ssl/private/<你的域名>.key \
  --fullchain-file /etc/ssl/certs/<你的域名>.fullchain.cer
```

---

## 各服务器证书记录

| 服务器 | 域名 | 证书路径 | 签发日期 | 到期日期 | 状态 |
|--------|------|----------|----------|----------|------|
| **node-22** | ai.qqbaidu.de5.net | `~/.acme.sh/ai.qqbaidu.de5.net_ecc/` | 2026-03-05 | 2026-06-03 | ✅ 有效 |
| **node-00** | - | - | - | - | ⏳ 待申请 |
| **node-11** | （内网，不需要） | - | - | - | ❌ 无需 |

---

## node-22 证书详情

**证书文件路径**：

| 文件 | 路径 |
|------|------|
| 证书 | `/root/.acme.sh/ai.qqbaidu.de5.net_ecc/ai.qqbaidu.de5.net.cer` |
| 私钥 | `/root/.acme.sh/ai.qqbaidu.de5.net_ecc/ai.qqbaidu.de5.net.key` |
| 中间证书 | `/root/.acme.sh/ai.qqbaidu.de5.net_ecc/ca.cer` |
| 完整链 | `/root/.acme.sh/ai.qqbaidu.de5.net_ecc/fullchain.cer` |

**服务器信息**：

| 项目 | 值 |
|------|-----|
| **服务器** | node-22（阿里云东京） |
| **公网 IP** | 43.167.177.86 |
| **系统** | OpenCloudOS 9.4 |

---

## 自动续期

acme.sh 会自动安装 cron 任务：

```bash
# 查看定时任务
crontab -l

# 手动续期测试
~/.acme.sh/acme.sh --renew -d <你的域名> --force --ecc
```

---

## 常见问题

### 1. 80 端口不通

**症状**: `Timeout during connect (likely firewall problem)`

**解决**:
1. 阿里云安全组 → 放行 TCP 80
2. 服务器防火墙 → `iptables -I INPUT -p tcp --dport 80 -j ACCEPT`
3. 确认域名解析正确 → `dig <你的域名>`

### 2. Cloudflare 代理问题

**症状**: `522 Connection timed out`

**解决**: Cloudflare 后台 → DNS → 关闭代理（灰色云朵）

### 3. DNS API 方式（备用方案）

如果 80 端口无法开放，使用 Cloudflare DNS API：

```bash
export CF_Token="YOUR_CLOUDFLARE_API_TOKEN"
~/.acme.sh/acme.sh --issue --dns dns_cf -d <你的域名> -m huhuun17@gmail.com --force
```

---

## 使用示例

### Nginx 配置

```nginx
server {
    listen 443 ssl http2;
    server_name <你的域名>;

    ssl_certificate /path/to/fullchain.cer;
    ssl_certificate_key /path/to/your.key;

    location / {
        root /var/www/html;
        index index.html;
    }
}
```

### Mihomo/XUI 配置

```yaml
# TLS 配置
cert_file: /path/to/fullchain.cer
key_file: /path/to/your.key
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-05
**适用范围**: 所有 Linux 服务器
