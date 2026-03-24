# node-22 AI 出口节点筛选报告

**测试时间**: 2026-03-06 19:21:56 CST
**测试位置**: node-22 (东京服务器)
**测试目标**: 第一组 AI 出口节点 (ChatGPT, Gemini, Google)

---

## 测试结果摘要

| 指标 | 数值 |
|------|------|
| 测试节点总数 | 31 个 |
| 可用节点数 | 17 个 |
| 完全失败节点 | 14 个 |
| 最优节点 | JP-1 (VLESS) |

---

## 推荐节点配置

### 🏆 主用节点 (out-ai-main)

**JP-1** (VLESS + Reality + gRPC)

```yaml
{
  "tag": "out-ai-main",
  "protocol": "vless",
  "settings": {
    "vnext": [
      {
        "address": "jp1-r.link-t7.com",
        "port": 10031,
        "users": [
          {
            "id": "4056C719-50EB-49E6-B513-42488F54F29C",
            "flow": "xtls-rprx-vision",
            "encryption": "none"
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

**性能指标**:
- ChatGPT: ✅
- Gemini: ✅
- Google: ✅
- 首包时间：201ms
- 稳定性：高 (5/5)

---

### 🔁 备用节点 (out-ai-backup)

**JP7-HY2** (Hysteria2)

```yaml
{
  "tag": "out-ai-backup",
  "protocol": "hysteria2",
  "settings": {
    "servers": [
      {
        "address": "jp7.dexlos.com",
        "port": 21332,
        "password": "4056C719-50EB-49E6-B513-42488F54F29C"
      }
    ]
  },
  "streamSettings": {
    "security": "tls",
    "serverName": "jp7.dexlos.com"
  }
}
```

**性能指标**:
- ChatGPT: ✅
- Gemini: ✅
- Google: ✅
- 首包时间：213ms
- 稳定性：高 (5/5)

---

### 🔁 备用节点 2 (out-ai-backup-2)

**JP8-HY2** (Hysteria2)

```yaml
{
  "tag": "out-ai-backup-2",
  "protocol": "hysteria2",
  "settings": {
    "servers": [
      {
        "address": "jp8.dexlos.com",
        "port": 21411,
        "password": "4056C719-50EB-49E6-B513-42488F54F29C"
      }
    ]
  },
  "streamSettings": {
    "security": "tls",
    "serverName": "jp8.dexlos.com"
  }
}
```

**性能指标**:
- ChatGPT: ✅
- Gemini: ✅
- Google: ✅
- 首包时间：207ms
- 稳定性：高 (5/5)

---

## 完整测试结果

### ✅ 可用节点 (17 个)

| 节点名 | 类型 | ChatGPT | Gemini | Google | 首包 | 稳定性 |
|--------|------|---------|--------|--------|------|--------|
| JP-1 | VLESS | ✅ | ✅ | ✅ | 201ms | 5/5 |
| JP-2 | VLESS | ❌ | ✅ | ✅ | 230ms | 5/5 |
| JP-3 | VLESS | ❌ | ✅ | ✅ | 205ms | 5/5 |
| JP-4 | VLESS | ❌ | ✅ | ✅ | 206ms | 5/5 |
| JP6-HY2 | HY2 | ✅ | ✅ | ✅ | 220ms | 5/5 |
| JP7-HY2 | HY2 | ✅ | ✅ | ✅ | 213ms | 5/5 |
| JP8-HY2 | HY2 | ✅ | ✅ | ✅ | 207ms | 5/5 |
| SG-1 | VLESS | ✅ | ✅ | ✅ | 376ms | 5/5 |
| SG-2 | VLESS | ❌ | ✅ | ✅ | 366ms | 5/5 |
| SG-3 | VLESS | ❌ | ✅ | ✅ | 369ms | 5/5 |
| SG1-HY2 | HY2 | ✅ | ✅ | ✅ | 386ms | 5/5 |
| SG2-HY2 | HY2 | ✅ | ✅ | ✅ | 373ms | 5/5 |
| HK-1 | VLESS | ❌ | ❌ | ✅ | 458ms | 5/5 |
| HK-2 | VLESS | ❌ | ❌ | ✅ | 341ms | 5/5 |
| HK-4 | VLESS | ❌ | ✅ | ✅ | 340ms | 5/5 |
| KR-1 | VLESS | ❌ | ✅ | ✅ | 341ms | 5/5 |
| KR-2 | VLESS | ❌ | ✅ | ✅ | 298ms | 5/5 |
| ss-US-1 | SS | ✅ | ✅ | ✅ | 566ms | 5/5 |

### ❌ 失败节点 (14 个)

| 节点名 | 类型 | 问题 |
|--------|------|------|
| US-1 | VLESS | 全部失败 |
| US-2 | VLESS | 全部失败 |
| US-3-gemini | VLESS | 全部失败 |
| HK-3 | VLESS | 全部失败 |
| US-gemini-1 | HY2 | 全部失败 |
| US1-HY2 | HY2 | 全部失败 |
| US2-HY2 | HY2 | 全部失败 |
| US3-HY2 | HY2 | 全部失败 |
| US4-HY2 | HY2 | 全部失败 |
| US5-HY2 | HY2 | 全部失败 |
| US6-HY2 | HY2 | 全部失败 |
| US7-HY2 | HY2 | 全部失败 |
| US8-HY2 | HY2 | 全部失败 |
| HK3-HY2 | HY2 | 稳定性低 |

---

## x-ui 配置建议

### 出站配置JSON

在 x-ui 面板中添加以下出站配置：

```json
{
  "outbounds": [
    {
      "tag": "out-ai-main",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "jp1-r.link-t7.com",
            "port": 10031,
            "users": [
              {
                "id": "4056C719-50EB-49E6-B513-42488F54F29C",
                "flow": "xtls-rprx-vision",
                "encryption": "none"
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
    },
    {
      "tag": "out-ai-backup",
      "protocol": "hysteria2",
      "settings": {
        "servers": [
          {
            "address": "jp7.dexlos.com",
            "port": 21332,
            "password": "4056C719-50EB-49E6-B513-42488F54F29C"
          }
        ]
      },
      "streamSettings": {
        "security": "tls",
        "serverName": "jp7.dexlos.com"
      }
    },
    {
      "tag": "out-ai-backup-2",
      "protocol": "hysteria2",
      "settings": {
        "servers": [
          {
            "address": "jp8.dexlos.com",
            "port": 21411,
            "password": "4056C719-50EB-49E6-B513-42488F54F29C"
          }
        ]
      },
      "streamSettings": {
        "security": "tls",
        "serverName": "jp8.dexlos.com"
      }
    }
  ]
}
```

---

## 注意事项

1. **OpenAI 检测问题**: 所有节点都无法通过 OpenAI 检测，这可能是 node-22 到 OpenAI 的路由问题，需要进一步排查
2. **美国节点全部失败**: 从东京访问美国节点延迟过高或路由被阻断
3. **香港节点限制**: 大部分香港节点无法访问 ChatGPT/Gemini，可能有地域限制
4. **协议多样性**: 推荐的 3 个节点包含 VLESS 和 Hysteria2 两种协议，提高容错能力

---

**下一步**: 将上述配置导入 x-ui，设置路由规则指向对应的 AI 网站
