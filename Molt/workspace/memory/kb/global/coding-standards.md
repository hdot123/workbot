---
type: [KB:GLOBAL]
title: "Coding Standards (SOP-001)"
created: 2026-02-17
updated: 2026-03-05
source: Manual
confidence: high
tags: [coding, standards, sop, shell, bash]
related: [mcp, nexus]
version: v4.1.2
status: active
last_verified: 2026-03-05
---

# 编码标准 (SOP-001)

> **版本**: V4.1.2
> **生效日期**: 2026-02-17
> **适用范围**: 所有由 Molt 生成的 .sh 脚本

---

## 环境注入规约

### 目标

确保项目在 Mac Pro 与阿里云节点之间的无缝复用。

### 强制要求

#### 标准化代码块

所有 .sh 脚本必须在 `#!/bin/bash` 下方立即插入以下逻辑：

```bash
# [Nexus Standard] 自动定位根目录并加载环境配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF_FILE="${PROJECT_ROOT}/.env.mcp"

if [ -f "$CONF_FILE" ]; then
  set -a && source "$CONF_FILE" && set +a
else
  echo "❌ Error: .env.mcp not found at ${CONF_FILE}"
  exit 1
fi
```

#### 路径引用规则

- **严禁使用硬编码物理路径**
- **必须通过 `${PROJECT_DIR}` 作为根路径引用**
- **所有相对路径应基于 `${PROJECT_ROOT}` 变量**

---

## 合规性检查

- [ ] 脚本包含标准化代码块
- [ ] 无硬编码物理路径
- [ ] 所有路径引用基于 `${PROJECT_ROOT}`
- [ ] `.env.mcp` 文件存在于项目根目录

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-02-17 | V4.1.2 | 初始版本 - Nexus V4.1.2 架构准则强制对齐 |
| 2026-03-05 | v4.1.2 | 迁移至 MRD 规范位置 `kb/global/`，添加 frontmatter |
