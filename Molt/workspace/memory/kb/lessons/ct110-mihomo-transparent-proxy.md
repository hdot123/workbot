---
type: [KB:LESSON]
title: CT110 Mihomo 透明代理快速部署指南
created: 2026-03-04
updated: 2026-03-04 17:30
source: Manual
confidence: high
tags: [ct110, mihomo, transparent-proxy, alpine, iptables]
related: [ct110, acr-private-registry]
status: active
version: v1.0
last_verified: 2026-03-08
---

# CT110 Mihomo 透明代理快速部署指南

## 10 分钟快速部署

### 前置条件

- CT110 容器运行中（Alpine Linux 3.22+）
- root SSH 访问权限
- 有效的代理订阅链接

### 快速部署脚本

```bash
# SSH 登录 CT110
ssh root@192.168.88.29

# === 1. 安装 Mihomo 二进制（1 分钟）===
curl -sL -o /tmp/mihomo.gz https://github.com/MetaCubeX/mihomo/releases/download/v1.19.0/mihomo-linux-amd64-v3-1.19.0.gz
gunzip -f /tmp/mihomo.gz
chmod +x /tmp/mihomo-linux-amd64-v3-1.19.0
mv /tmp/mihomo-linux-amd64-v3-1.19.0 /usr/local/bin/mihomo
chmod +x /usr/local/bin/mihomo

# 验证版本
/usr/local/bin/mihomo -v

# === 2. 创建配置目录（30 秒）===
mkdir -p /root/.config/mihomo/ui

# === 3. 下载控制面板 UI（1 分钟）===
curl -sL -o /tmp/ui.zip https://github.com/MetaCubeX/metacubexd/archive/refs/heads/gh-pages.zip
unzip -q -o /tmp/ui.zip -d /tmp/
cp -r /tmp/metacubexd-gh-pages/* /root/.config/mihomo/ui/
rm -rf /tmp/ui.zip /tmp/metacubexd-gh-pages

# === 4. 下载 Country.mmdb（1 分钟）===
curl -sL -o /root/.config/mihomo/Country.mmdb https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/country.mmdb

# === 5. 创建配置文件（2 分钟）===
# 编辑订阅链接和代理组配置
```

### 配置文件 `/root/.config/mihomo/config.yaml`

```yaml
# Mihomo 配置 - 透明代理模式
mixed-port: 7890
redir-port: 7892
external-controller: 0.0.0.0:9090
external-ui: /root/.config/mihomo/ui
allow-lan: true
bind-address: '*'
mode: rule
log-level: info
ipv6: false
unified-delay: true
tcp-concurrent: true

tun:
  enable: false

dns:
  enable: true
  listen: 0.0.0.0:53
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - '*.lan'
    - '*.local'
    - '+.stun.*.*'
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - https://dns.alidns.com/dns-query
  fallback:
    - https://1.1.1.1/dns-query
  fallback-filter:
    geoip: false

proxy-providers:
  mitce:
    type: http
    url: 'https://app.mitce.net/?sid=394560&token=154c40c22ab789aae3ea'  # ⚠️ 替换为你的订阅
    interval: 3600
    path: ./proxy-providers/mitce.yaml
    health-check:
      enable: true
      url: http://www.gstatic.com/generate_204
      interval: 300

proxy-groups:
  - name: Proxy
    type: url-test
    use: [mitce]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50

  - name: HK
    type: url-test
    filter: '🇭🇰|香港|HK'
    use: [mitce]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50

  - name: Gemini
    type: url-test
    filter: '🇯🇵|日本|JP|🇸🇬|新加坡 |SG|🇺🇸|美国|US'
    exclude: '🇭🇰|香港|HK'
    use: [mitce]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50

  - name: AI
    type: url-test
    filter: '🇺🇸|美国|US|🇯🇵|日本|JP|🇸🇬|新加坡 |SG|🇰🇷|韩国|KR|🇹🇼|台湾|TW'
    exclude: '🇭🇰|香港|HK'
    use: [mitce]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50

rules:
  # YouTube 走 HK
  - DOMAIN-SUFFIX,youtube.com,HK
  - DOMAIN-SUFFIX,ytimg.com,HK
  - DOMAIN-SUFFIX,googlevideo.com,HK
  
  # Gemini 走非 HK
  - DOMAIN-SUFFIX,googleapis.com,Gemini
  - DOMAIN-SUFFIX,googleapis.cn,Gemini
  - DOMAIN,gemini.google.com,Gemini
  
  # AI 服务走非 HK
  - DOMAIN-SUFFIX,openai.com,AI
  - DOMAIN-SUFFIX,chatgpt.com,AI
  - DOMAIN-SUFFIX,anthropic.com,AI
  - DOMAIN-SUFFIX,claude.ai,AI
  - DOMAIN-SUFFIX,twitter.com,AI
  - DOMAIN-SUFFIX,x.com,AI
  
  # 国内直连
  - GEOIP,CN,DIRECT
  
  # 默认
  - MATCH,Proxy
```

```bash
# === 6. 启动 Mihomo（30 秒）===
nohup /usr/local/bin/mihomo -d /root/.config/mihomo > /tmp/mihomo.log 2>&1 &

# 验证启动
ps aux | grep mihomo | grep -v grep
netstat -tlnp | grep -E '7890|7892|9090|53'

# === 7. 配置 iptables 透明代理（2 分钟）===
# 清空现有规则
iptables -t nat -F PREROUTING
iptables -t nat -F POSTROUTING
iptables -F FORWARD

# PREROUTING - 重定向外部流量
iptables -t nat -A PREROUTING -d 192.168.88.29/32 -j RETURN
iptables -t nat -A PREROUTING -p tcp --dport 53 -j RETURN
iptables -t nat -A PREROUTING -p udp --dport 53 -j RETURN
iptables -t nat -A PREROUTING -d 10.0.0.0/8 -j RETURN
iptables -t nat -A PREROUTING -d 172.16.0.0/12 -j RETURN
iptables -t nat -A PREROUTING -d 127.0.0.0/8 -j RETURN

# 重定向 HTTP/HTTPS 到 redir-port
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 7892
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 7892

# FORWARD - 允许转发
iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# POSTROUTING - MASQUERADE
iptables -t nat -A POSTROUTING -j MASQUERADE

# 验证规则
iptables -t nat -L PREROUTING -n -v
iptables -L FORWARD -n -v

# === 8. 配置开机自启（1 分钟）===
# 创建启动脚本
cat > /etc/init.d/mihomo << 'INIT'
#!/sbin/openrc-run

name="mihomo"
description="Mihomo transparent proxy service"
command="/usr/local/bin/mihomo"
command_args="-d /root/.config/mihomo"
command_background="yes"
pidfile="/var/run/mihomo.pid"

depend() {
    need net
    use logger dns
}

start_pre() {
    # 等待网络就绪
    sleep 2
    
    # 配置 iptables
    iptables -t nat -F PREROUTING
    iptables -t nat -F POSTROUTING
    iptables -F FORWARD
    
    iptables -t nat -A PREROUTING -d 192.168.88.29/32 -j RETURN
    iptables -t nat -A PREROUTING -p tcp --dport 53 -j RETURN
    iptables -t nat -A PREROUTING -p udp --dport 53 -j RETURN
    iptables -t nat -A PREROUTING -d 10.0.0.0/8 -j RETURN
    iptables -t nat -A PREROUTING -d 172.16.0.0/12 -j RETURN
    iptables -t nat -A PREROUTING -d 127.0.0.0/8 -j RETURN
    iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 7892
    iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 7892
    
    iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT
    iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -t nat -A POSTROUTING -j MASQUERADE
}

stop_post() {
    iptables -t nat -F PREROUTING
    iptables -t nat -F POSTROUTING
    iptables -F FORWARD
}
INIT

chmod +x /etc/init.d/mihomo
rc-update add mihomo default

# 测试自启
rc-service mihomo restart
```

## 验证测试

### 1. 服务状态检查

```bash
# 进程状态
ps aux | grep mihomo | grep -v grep

# 端口监听
netstat -tlnp | grep -E '7890|7892|9090|53'

# 代理组状态
curl -s http://127.0.0.1:9090/proxies/Proxy | grep -o '"now":"[^"]*"'
curl -s http://127.0.0.1:9090/proxies/HK | grep -o '"now":"[^"]*"'
curl -s http://127.0.0.1:9090/proxies/Gemini | grep -o '"now":"[^"]*"'
curl -s http://127.0.0.1:9090/proxies/AI | grep -o '"now":"[^"]*"'
```

### 2. 本地代理测试

```bash
# HTTP 测试
http_proxy=http://127.0.0.1:7890 curl -s -o /dev/null -w '%{http_code}' http://www.baidu.com

# HTTPS 测试
https_proxy=http://127.0.0.1:7890 curl -s -o /dev/null -w '%{http_code}' https://www.google.com
```

### 3. iptables 流量检查

```bash
# 查看计数器
iptables -t nat -L PREROUTING -n -v

# 应该有数据包在 REDIRECT 规则上计数
```

### 4. 手机客户端测试

1. 手机设置网关为 `192.168.88.29`
2. 访问 http://www.baidu.com（HTTP）
3. 访问 https://www.google.com（HTTPS）
4. 访问 https://chatgpt.com（AI 分流）
5. 访问 https://www.youtube.com（HK 分流）

## 访问信息

| 服务 | 地址 |
|------|------|
| **HTTP/SOCKS 代理** | `http://192.168.88.29:7890` |
| **透明代理重定向** | `192.168.88.29:7892` |
| **控制面板** | `http://192.168.88.29:9090/ui/` |
| **DNS 服务** | `192.168.88.29:53` |

## 常用命令

```bash
# 重启 Mihomo
pkill mihomo && nohup /usr/local/bin/mihomo -d /root/.config/mihomo > /tmp/mihomo.log 2>&1 &

# 查看日志
tail -f /tmp/mihomo.log

# 查看连接
curl -s http://127.0.0.1:9090/connections

# 强制刷新订阅
rm /root/.config/mihomo/proxy-providers/mitce.yaml
curl -s http://127.0.0.1:9090/providers/proxies | grep mitce

# 查看 iptables 计数
iptables -t nat -L PREROUTING -n -v
```

## 故障排查

### 问题 1：节点加载失败
```bash
# 检查订阅链接
curl -s 'https://app.mitce.net/?sid=394560&token=154c40c22ab789aae3ea' | head -5

# 删除缓存强制刷新
rm /root/.config/mihomo/proxy-providers/mitce.yaml
pkill mihomo
nohup /usr/local/bin/mihomo -d /root/.config/mihomo > /tmp/mihomo.log 2>&1 &
```

### 问题 2：iptables 规则不生效
```bash
# 检查 IP 转发
cat /proc/sys/net/ipv4/ip_forward  # 应该为 1

# 启用转发
echo 1 > /proc/sys/net/ipv4/ip_forward

# 检查规则顺序
iptables -t nat -L PREROUTING -n -v
```

### 问题 3：Mihomo 无法启动
```bash
# 检查配置文件
/usr/local/bin/mihomo -t -d /root/.config/mihomo

# 查看详细日志
cat /tmp/mihomo.log
```

## 更新历史

- **2026-03-04 17:30**: 初始创建，记录完整部署流程和配置
- **2026-03-04 17:00**: 解决透明代理问题（使用 redir-port 7892）
- **2026-03-04 16:00**: 完成代理组配置（HK/Gemini/AI）

