---
type: [KB:LESSON]
title: "Lesson: 运维相关经验"
created: 2026-03-04
updated: 2026-03-04
last_verified: 2026-03-04
status: active
tags: []
confidence: high
source: Manual
version: v1.0
related: []
---

# Lesson: 运维相关经验

## 交换内存配置 (Linux)
```bash
# 创建交换文件 (2GB)
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```
- **关键**: 必须添加到 `/etc/fstab` 才能长期生效
- **权限**: 交换文件权限必须是 600

## 火山引擎海外节点镜像源
- **问题**: 默认 `mirrors.ivolces.com` 在海外无法解析
- **解决**: 替换为 Ubuntu 官方源
```bash
cat > /etc/apt/sources.list << 'EOF'
deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ noble-security main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-backports main restricted universe multiverse
EOF
apt update
```

## 双子星系统运维 [已退役 2026-02-27]
- JimiBot 和 LimeBot 已删除
- 保留历史记录供参考
- 诊断顺序: 端口监听 → 进程 PID → 服务状态 → 日志诊断

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "### 运维相关" (标题明确)
- confidence: high
