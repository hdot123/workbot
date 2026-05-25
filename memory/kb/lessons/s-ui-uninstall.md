---
type: [KB:LESSON]
title: S-UI (Sing-Box UI) 完全卸载文档
created: 2026-03-05
source: Manual
confidence: high
tags: [s-ui, sing-box, uninstall, cleanup]
status: active
version: v1.0
last_verified: 2026-03-08
updated: 2026-03-08
related: []
---

# S-UI 完全卸载文档

> 标准的 `s-ui uninstall` 命令可能无法完全清理所有残留，本文档提供彻底卸载的方法。

---

## 一、标准卸载

```bash
# 方法 1：使用 s-ui 命令
s-ui uninstall

# 方法 2：手动卸载
systemctl stop s-ui
systemctl disable s-ui
rm -f /etc/systemd/system/s-ui.service
rm -rf /usr/local/s-ui
rm -rf /etc/s-ui
systemctl daemon-reload
```

---

## 二、清理残留进程（重要）

` s-ui log` 命令会产生后台日志进程，这些进程不会随 `s-ui uninstall` 自动清理：

```bash
# 查看所有 s-ui 相关进程
ps aux | grep -E 's-ui|sui' | grep -v grep

# 常见残留进程类型：
# - /bin/bash /usr/bin/s-ui log
# - journalctl -u s-ui.service -e --no-pager -f
# - bash -c s-ui log 2>&1 | tail -30

# 批量杀掉所有残留进程
pkill -9 -f 's-ui log'
pkill -9 -f 'journalctl.*s-ui'

# 或者更彻底的方法
ps aux | grep -E 's-ui|sui' | grep -v grep | awk '{print $2}' | xargs kill -9
```

---

## 三、删除残留文件

```bash
# 删除主要目录
rm -rf /usr/local/s-ui
rm -rf /etc/s-ui

# 删除 s-ui 脚本
rm -f /usr/bin/s-ui

# 清理 systemd 配置
rm -f /etc/systemd/system/s-ui.service
rm -rf /etc/systemd/system/multi-user.target.wants/s-ui.service

# 重载 systemd
systemctl daemon-reload
systemctl reset-failed
```

---

## 四、查找并删除遗漏文件

```bash
# 查找所有 s-ui 相关文件
find / -path /proc -prune -o -path /sys -prune -o -name '*s-ui*' -type f -print 2>/dev/null

# 查找所有 sui 二进制文件
find / -path /proc -prune -o -path /sys -prune -o -name 'sui' -type f -print 2>/dev/null

# 查找数据库文件
find / -name 's-ui.db' 2>/dev/null

# 删除找到的文件（排除 npm/pnpm/node_modules 中的无关文件）
find / -path /proc -prune -o -path /sys -prune -o -name '*s-ui*' -type f -print 2>/dev/null | \
  grep -v npm | grep -v pnpm | grep -v node_modules | grep -v larksuite | \
  xargs rm -rf
```

---

## 五、验证卸载

```bash
# 1. 检查进程
ps aux | grep -E 's-ui|sui' | grep -v grep
# 应该无输出（或只有 grep 自身）

# 2. 检查端口（默认 2095 和 2096）
ss -tlnp | grep -E '2095|2096|18422'
# 应该无输出

# 3. 检查文件
ls /usr/local/s-ui 2>&1
ls /etc/s-ui 2>&1
# 应该显示 "No such file or directory"

# 4. 检查命令
which s-ui 2>&1
# 应该无输出

# 5. 检查 systemd 服务
systemctl list-units --all | grep s-ui
# 应该无输出
```

---

## 六、一键彻底卸载脚本

```bash
#!/bin/bash
# S-UI 完全卸载脚本

echo "Stopping S-UI service..."
systemctl stop s-ui 2>/dev/null
systemctl disable s-ui 2>/dev/null

echo "Killing残留进程..."
pkill -9 -f 's-ui log'
pkill -9 -f 'journalctl.*s-ui'
ps aux | grep -E 's-ui|sui' | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

echo "删除文件..."
rm -rf /usr/local/s-ui
rm -rf /etc/s-ui
rm -f /usr/bin/s-ui
rm -f /etc/systemd/system/s-ui.service
rm -rf /etc/systemd/system/multi-user.target.wants/s-ui.service

echo "重载 systemd..."
systemctl daemon-reload
systemctl reset-failed

echo "清理残留文件..."
find / -path /proc -prune -o -path /sys -prune -o -name '*s-ui*' -type f -print 2>/dev/null | \
  grep -v npm | grep -v pnpm | grep -v node_modules | grep -v larksuite | \
  xargs rm -rf 2>/dev/null

echo "验证..."
PORTS=$(ss -tlnp | grep -E '2095|2096|18422' | wc -l)
PROCS=$(ps aux | grep -E 's-ui|sui' | grep -v grep | wc -l)

if [ "$PORTS" -eq 0 ] && [ "$PROCS" -eq 0 ]; then
    echo "✅ S-UI 已完全卸载"
else
    echo "⚠️ 可能还有残留，请手动检查"
    echo "剩余端口数：$PORTS"
    echo "剩余进程数：$PROCS"
fi
```

---

## 七、常见问题

### Q1: 为什么 `s-ui uninstall` 后还能看到进程？
**A:** `s-ui log` 命令启动的日志查看会话是独立的 bash 进程，不会被 `s-ui uninstall` 清理。

### Q2: journalctl 进程能直接 kill 吗？
**A:** 可以，这些只是日志查看进程，杀掉不会影响系统。

### Q3: 数据库文件在哪里？
**A:** 默认在 `/usr/local/s-ui/db/s-ui.db` 或 `/etc/s-ui/db/s-ui.db`

### Q4: 为什么 find 命令要排除 npm/pnpm？
**A:** 因为某些 npm 包（如 `@larksuiteoapi`）名称中包含 `s-ui` 字符串，但不是 S-UI 相关。

---

**文档版本**: v1.0
**最后更新**: 2026-03-05
**适用范围**: 所有 Linux 服务器
