# node-22 x-ui 路由配置 - 最终版

**更新时间**: 2026-03-07 00:03
**状态**: ✅ 已应用

---

## 配置结构

```
┌─────────────────────────────────────────────────────────┐
│                    路由规则 (routing.rules)              │
├─────────────────────────────────────────────────────────┤
│ 1. geosite:openai        → out-openai (Shadowsocks)    │
│ 2. Gemini 域名            → out-gemini (VLESS JP-3)    │
│ 3. Google/Twitter/YouTube → out-media (VLESS HK-1)     │
│ 4. 默认 (tcp,udp)         → out-media (VLESS HK-1)     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                    出站配置 (outbounds)                  │
├─────────────────────────────────────────────────────────┤
│ out-openai  → SS 美国 (155.117.87.123:10378)           │
│ out-gemini  → VLESS 日本 (jp3-r.link-t7.com:10033)     │
│ out-media   → VLESS 香港 (hk1-r.link-t7.com:10126)     │
│ direct      → Freedom (直连)                            │
└─────────────────────────────────────────────────────────┘
```

---

## 路由规则详情

### 规则 1: OpenAI
```json
{
  "type": "field",
  "domain": ["geosite:openai"],
  "outboundTag": "out-openai"
}
```
- **匹配**: ChatGPT、OpenAI API 等
- **出站**: Shadowsocks 美国节点

### 规则 2: Gemini
```json
{
  "type": "field",
  "domain": [
    "domain:gemini.google.com",
    "domain:generativelanguage.googleapis.com",
    "domain:aistudio.google.com"
  ],
  "outboundTag": "out-gemini"
}
```
- **匹配**: Gemini AI 相关域名
- **出站**: VLESS 日本节点 (JP-3)

### 规则 3: 媒体/搜索
```json
{
  "type": "field",
  "domain": [
    "geosite:google",
    "geosite:twitter",
    "geosite:youtube"
  ],
  "outboundTag": "out-media"
}
```
- **匹配**: Google 搜索、Twitter/X、YouTube
- **出站**: VLESS 香港节点 (HK-1)

### 规则 4: 默认路由
```json
{
  "type": "field",
  "network": "tcp,udp",
  "outboundTag": "out-media"
}
```
- **匹配**: 所有未命中上述规则的流量
- **出站**: VLESS 香港节点 (HK-1)

---

## 出站节点详情

### out-openai (Shadowsocks)
```json
{
  "tag": "out-openai",
  "protocol": "shadowsocks",
  "settings": {
    "servers": [
      {
        "address": "155.117.87.123",
        "port": 10378,
        "method": "2022-blake3-aes-128-gcm",
        "password": "MjAyNjJrNXN6WWtHQVZPeA==:NDA1NkM3MTktNTBFQi00OQ=="
      }
    ]
  }
}
```

### out-gemini (VLESS 日本)
```json
{
  "tag": "out-gemini",
  "protocol": "vless",
  "settings": {
    "vnext": [
      {
        "address": "jp3-r.link-t7.com",
        "port": 10033,
        "users": [
          {
            "id": "4056C719-50EB-49E6-B513-42488F54F29C",
            "encryption": "none",
            "flow": "xtls-rprx-vision"
          }
        ]
      }
    ]
  },
  "streamSettings": {
    "network": "grpc",
    "security": "reality",
    "realitySettings": {
      "serverName": "s0.awsstatic.com",
      "publicKey": "wOu-BMrXvk9KX23JZrlpUlF4SMjDcejm0vNECdhy5xE",
      "shortId": "686c0ef0",
      "fingerprint": "chrome"
    },
    "grpcSettings": {
      "serviceName": "update"
    }
  }
}
```

### out-media (VLESS 香港)
```json
{
  "tag": "out-media",
  "protocol": "vless",
  "settings": {
    "vnext": [
      {
        "address": "hk1-r.link-t7.com",
        "port": 10126,
        "users": [
          {
            "id": "4056C719-50EB-49E6-B513-42488F54F29C",
            "encryption": "none",
            "flow": "xtls-rprx-vision"
          }
        ]
      }
    ]
  },
  "streamSettings": {
    "network": "grpc",
    "security": "reality",
    "realitySettings": {
      "serverName": "s0.awsstatic.com",
      "publicKey": "wOu-BMrXvk9KX23JZrlpUlF4SMjDcejm0vNECdhy5xE",
      "shortId": "686c0ef0",
      "fingerprint": "chrome"
    },
    "grpcSettings": {
      "serviceName": "update"
    }
  }
}
```

### direct (Freedom)
```json
{
  "protocol": "freedom",
  "tag": "direct",
  "settings": {
    "domainStrategy": "AsIs"
  }
}
```

---

## 配置文件

- **本地配置**: `workspace/projects/node-22-x-ui-config.json`
- **服务器临时文件**: `node-22:/tmp/node-22-x-ui-config.json`

---

## 部署命令

```bash
# 1. 上传配置文件
scp node-22-x-ui-config.json node-22:/tmp/node-22-x-ui-config.json

# 2. SSH 登录并执行 Python 脚本更新数据库
ssh node-22 '
python3 << '\''PYTHON'\''
import sqlite3
import json

with open("/tmp/node-22-x-ui-config.json", "r") as f:
    config = json.load(f)

routing = json.dumps(config["routing"], separators=(",", ":"))
outbounds = json.dumps(config["outbounds"], separators=(",", ":"))

conn = sqlite3.connect("/etc/x-ui/x-ui.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM settings WHERE key = '\''subRoutingRules'\''")
cursor.execute("INSERT INTO settings (key, value) VALUES ('\''subRoutingRules'\'', ?)", (routing,))

cursor.execute("DELETE FROM settings WHERE key = '\''outbounds'\''")
cursor.execute("INSERT INTO settings (key, value) VALUES ('\''outbounds'\'', ?)", (outbounds,))

conn.commit()
conn.close()
print("数据库更新成功!")
PYTHON

x-ui restart-xray
'
```

---

## 验证命令

```bash
# 检查配置长度
ssh node-22 "sqlite3 /etc/x-ui/x-ui.db \"SELECT key, length(value) FROM settings WHERE key IN ('subRoutingRules', 'outbounds');\""

# 查看路由规则
ssh node-22 "sqlite3 /etc/x-ui/x-ui.db \"SELECT value FROM settings WHERE key = 'subRoutingRules';\" | jq ."

# 查看出站配置
ssh node-22 "sqlite3 /etc/x-ui/x-ui.db \"SELECT value FROM settings WHERE key = 'outbounds';\" | jq '.[] | {tag, protocol}'"

# 检查 xray 状态
ssh node-22 "x-ui status"

# 查看 xray 日志
ssh node-22 "journalctl -u x-ui --no-pager -n 20 | grep XRAY"
```

---

## 更新历史

| 时间 | 操作 | 状态 |
|------|------|------|
| 2026-03-07 00:03 | 应用简洁版路由配置 (4 rules + 4 outbounds) | ✅ 成功 |
| 2026-03-06 23:58 | 首次尝试更新配置 | ⚠️ 部分成功 |
| 2026-03-06 23:53 | 创建初始配置 | - |

---

## 流量走向说明

1. **访问 ChatGPT** → 匹配 `geosite:openai` → `out-openai` (SS 美国)
2. **访问 Gemini** → 匹配 Gemini 域名 → `out-gemini` (VLESS 日本)
3. **访问 YouTube/Google/Twitter** → 匹配媒体规则 → `out-media` (VLESS 香港)
4. **其他所有流量** → 匹配默认规则 → `out-media` (VLESS 香港)
