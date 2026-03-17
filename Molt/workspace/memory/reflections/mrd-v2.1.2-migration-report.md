# MRD v2.1.2 规范迁移执行报告

**执行日期**: 2026-03-05
**规范版本**: v2.1.2
**执行者**: Molt (系统)
**状态**: ✅ 已完成

---

## 📋 迁移目标

按照《记忆分层路由总设计 v2.1.2》规范，将历史文档从活跃索引区域迁移至冷存储层（`archive-memory/raw/`），确保：

1. 历史噪音永不污染索引
2. KB 层保持唯一 canonical 状态
3. 证据完整保留，永不删除

---

## ✅ 迁移执行清单

### 归档到 `archive-memory/raw/standards/`

| 文件 | 原路径 | 归档原因 | Canonical 替代 |
|------|--------|---------|---------------|
| `sop-002-directory-restructure.md` | standards/ | 历史执行记录，已完成 | kb/lessons/runbook.md |
| `sop-003-mcp-verification.md` | standards/ | 历史验证报告 | kb/lessons/mcp-config.md |
| `sop-004-skills-migration.md` | standards/ | 历史迁移记录 | kb/lessons/runbook.md |
| `sop-005-path-fixes.md` | standards/ | 历史修复记录 | kb/lessons/git.md |
| `audit-report-2026-02-10.md` | standards/ | 历史审计报告 | kb/decisions/alignment-report-2026-02-10.md |
| `mcp-tree-overview.md` | standards/ | 内容冗余 | kb/lessons/mcp-config.md |
| `myproject-overview.md` | standards/ | 外部项目文档 | 无（不属于本系统） |
| `sop-002-operator-admission.md` | standards/ | 草案阶段 | kb/lessons/mcp-config.md |
| `sop-002-mcp-deployment-baseline.md` | standards/ | 草案阶段 | kb/lessons/mcp-config.md |
| `alignment-report-2026-02-10.md` | standards/ | 历史对齐报告 | kb/decisions/alignment-report-2026-02-10.md |
| `sop-006-tailscale-baseline.md` | standards/ | 历史基线文档 | kb/lessons/tailscale-baseline-sop.md |
| `sop-001-coding-standards.md` | standards/ | 历史编码规范 | kb/global/coding-standards.md |

### 归档到 `archive-memory/raw/` 根目录

| 文件 | 归档原因 |
|------|---------|
| 旧日志文件 (2026-02-XX.md) | 历史日志，已迁移至 log/ |
| 旧 MEMORY.md 备份 | 启动器精简后的历史版本 |
| 过程 dump 文件 | 临时导出，无索引价值 |

---

## 📁 迁移后目录结构

```
/Users/busiji/passkills/
├── workspace/
│   ├── MEMORY.md                    # L0 Boot 层（<20 行）
│   ├── NOW.md                       # L1 State 层（覆写）
│   └── memory/
│       ├── log/                     # L2 Fact 层
│       │   ├── 2026-03-02.md
│       │   ├── 2026-03-03.md
│       │   ├── 2026-03-04.md
│       │   └── 2026-03-05.md
│       └── kb/                      # L3 Knowledge 层（索引核心）
│           ├── global/              # 跨项目规范
│           │   ├── coding-standards.md
│           │   └── versions/
│           │       └── memory-router-design-v2.1.2.md
│           ├── projects/            # 项目专属
│           ├── lessons/             # 经验教训
│           ├── decisions/           # 决策记录
│           ├── preferences/         # 用户偏好
│           ├── people/              # 人物档案
│           └── reference/           # 参考资料
│
└── archive-memory/                  # L4 Cold 层（不索引）
    ├── raw/                         # 历史资料
    │   ├── standards/               # 归档的 standards 文档
    │   │   ├── sop-002-directory-restructure.md
    │   │   ├── sop-003-mcp-verification.md
    │   │   ├── sop-004-skills-migration.md
    │   │   ├── sop-005-path-fixes.md
    │   │   ├── sop-006-tailscale-baseline.md
    │   │   ├── audit-report-2026-02-10.md
    │   │   ├── mcp-tree-overview.md
    │   │   └── ...
    │   └── *.md                     # 其他历史文件
    └── invalid/
        └── INVALID-MEMORY.md        # 冲突/错误记忆
```

---

## 🔍 Canonical 映射验证

### 已建立的 Canonical 路径

| 知识类型 | Canonical 路径 | 状态 |
|---------|---------------|------|
| 编码规范 | `kb/global/coding-standards.md` | ✅ |
| 记忆路由设计 | `kb/global/versions/memory-router-design-v2.1.2.md` | ✅ |
| Tailscale 基线 | `kb/lessons/tailscale-baseline-sop.md` | ✅ |
| MCP 配置 | `kb/lessons/mcp-config.md` | ✅ |
| 运维手册 | `kb/lessons/runbook.md` | ✅ |
| Git 规范 | `kb/lessons/git.md` | ✅ |
| 对齐报告 | `kb/decisions/alignment-report-2026-02-10.md` | ✅ |

---

## 📊 统计数据

### 迁移统计

| 分类 | 数量 |
|------|------|
| 归档到 raw/standards/ | 12 个文件 |
| 归档到 raw/ 根目录 | 多个日志/备份文件 |
| 建立 Canonical 映射 | 7 个核心文档 |

### 索引影响

| 指标 | 迁移前 | 迁移后 |
|------|--------|--------|
| standards/ 活跃文档 | 12+ | 0 |
| kb/ 索引文档 | ~20 | ~34 |
| raw/ 归档文档 | ~10 | ~25+ |

---

## 🚀 后续维护指南

### 新文档写入规则

1. **事实写 log/**: `workspace/memory/log/YYYY-MM-DD.md`
2. **可复用写 kb/**: `workspace/memory/kb/<category>/`
3. **产物写 projects/**: `workspace/projects/`
4. **错误写 invalid/**: `archive-memory/invalid/INVALID-MEMORY.md`
5. **历史写 raw/**: `archive-memory/raw/`

### 归档触发条件

当文档满足以下任一条件时，应迁移至 `archive-memory/raw/`：

- [ ] 执行已完成，无后续参考价值
- [ ] 内容已被 KB 层 canonical 替代
- [ ] 属于外部项目或临时导出
- [ ] 草案阶段被正式文档取代

### 归档操作模板

```bash
# 1. 移动文件
mv workspace/standards/<file>.md archive-memory/raw/standards/

# 2. 添加归档标记（文件头部）
> ⚠️ **[ARCHIVE:RAW] 已归档历史文档**
> - **归档日期**: YYYY-MM-DD
> - **原因**: <原因说明>
> - **Canonical**: <KB 替代路径（如有）>
> - **状态**: DO NOT USE AS CANONICAL；仅供历史参考，不作为知识检索源
```

---

## ✅ 验证清单

- [x] 所有历史 SOP 文档已归档
- [x] 所有归档文档添加了 `[ARCHIVE:RAW]` 标记
- [x] KB 层 canonical 路径已建立
- [x] 索引配置正确（raw/ 不入库）
- [x] 目录结构符合 MRD v2.1.2 规范

---

## 📝 变更记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0.0 | 2026-03-05 | 初始版本，完成 MRD v2.1.2 规范迁移 |

---

**执行状态**: ✅ 已完成
**最后更新**: 2026-03-05
**维护者**: Molt 系统

---

> **一句话铁律**: 事实写 log，可复用写 kb，产物写 projects，错误写 invalid，历史写 raw；索引核心看 docs+kb，archive-memory 永不入库。
