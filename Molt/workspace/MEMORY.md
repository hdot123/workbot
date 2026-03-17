# MEMORY - Boot (永不膨胀)

## Load Order (严格按此顺序读，缺一不可)
1. NOW.md
2. ROUTER.md
3. memory/short-index.md
4. memory/log/YYYY-MM-DD.md

## Quick Reference (快速引用)
- **MRD** = 记忆路由设计规范 → `memory/kb/global/memory-router-design.md`

## 永久铁律（违背=系统错误）
- ONLY NOW.md 可以被覆写
- memory/：append-only 或 read-first-CRUD，禁止直接 write 覆写
- 决策/偏好/教训必须写 kb/
- 冲突必须写 CONFLICT block，禁止静默覆盖
