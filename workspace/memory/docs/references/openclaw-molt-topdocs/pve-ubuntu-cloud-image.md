# PVE 部署 Ubuntu 24.04 Cloud Image 流程

## 📋 概述
在 Proxmox VE (PVE) 上部署 Ubuntu 24.04 Cloud Image 的完整流程。

---

## 1️⃣ 下载镜像

### 方法一：在 PVE Shell 中下载
```bash
cd /tmp
wget https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img
```

### 方法二：本地下载后上传
- 官方地址：https://cloud-images.ubuntu.com/releases/24.04/release/
- 文件名：`ubuntu-24.04-server-cloudimg-amd64.img`

---

## 2️⃣ 创建虚拟机

### 基础配置
```bash
# 创建 VM（ID=105，名称=ubuntu-2404）
qm create 105 --name "ubuntu-2404" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# 导入磁盘镜像到 nvme-dot 存储
qm importdisk 105 /var/lib/vz/template/iso/ubuntu-24.04-server-cloudimg-amd64.img nvme-dot

# 挂载磁盘（SCSI 控制器 + 磁盘）
qm set 105 --scsihw virtio-scsi-pci --scsi0 nvme-dot:vm-105-disk-0

# 设置启动盘
qm set 105 --boot c --bootdisk scsi0
```

### 参数说明
- `--memory 2048`：2GB 内存
- `--cores 2`：2 核 CPU
- `--net0 virtio,bridge=vmbr0`：网络配置（桥接模式）
- `nvme-dot`：PVE 存储名称（NVMe 存储）

---

## 3️⃣ Cloud-Init 配置

### 创建配置文件
```bash
cat > /tmp/user-data.yaml <<EOF
#cloud-config
hostname: ubuntu-2404
manage_etc_hosts: true
users:
  - name: root
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFr9HGklygIisIj/StWvu+LLwsRyXEmPejP4BjDPUTar xun201811@gmail.com
    lock_passwd: false
    shell: /bin/bash
chpasswd:
  expire: false
  list:
    - root:<你的密码>
runcmd:
  - systemctl enable ssh
  - systemctl start ssh
EOF
```

### 生成 Cloud-Init ISO
```bash
# 安装工具（如果未安装）
apt-get install cloud-image-utils -y

# 生成 seed.iso
cloud-localds /tmp/seed.iso /tmp/user-data.yaml

# 挂载 ISO 到 VM
qm set 105 --cdrom local:iso/seed.iso
```

---

## 4️⃣ 网络配置（可选）

### 静态 IP 配置
```bash
qm set 105 --ipconfig0 ip=192.168.1.105/24,gw=192.168.1.1
```

### DHCP 配置（默认）
```bash
qm set 105 --ipconfig0 ip=dhcp
```

---

## 5️⃣ 启动与验证

### 启动虚拟机
```bash
qm start 105
```

### SSH 连接
```bash
# 等待 1-2 分钟后连接
ssh root@192.168.1.100

# 或使用域名（如果配置了 DNS）
ssh root@ubuntu-2404
```

### 验证命令
```bash
# 检查系统版本
cat /etc/os-release

# 检查网络
ip addr show

# 检查 SSH 服务
systemctl status ssh
```

---

## ⚡ 快捷方式（PVE GUI）

### 1. 上传镜像
- PVE → local (storage) → ISO Images → Upload
- 选择 `ubuntu-24.04-server-cloudimg-amd64.img`

### 2. 创建虚拟机
- 点击 "Create VM"
- OS → Linux 6.x - Kernel 6.x
- System → Default
- Disk → SCSI0 → Import from → 选择镜像
- CPU → Cores: 2
- Memory → Memory (MiB): 2048
- Network → Bridge: vmbr0

### 3. Cloud-Init 配置（GUI）
- VM → Cloud-Init
- User: root
- Password: <你的密码>
- SSH Public Key: `ssh-ed25519 AAAA...`
- IP Config: ip=dhcp 或 ip=192.168.1.100/24,gw=192.168.1.1

### 4. 启动
- 点击 "Start"
- 等待 1-2 分钟
- SSH 连接

---

## 🔧 高级配置

### 1. 扩展磁盘
```bash
# 扩展到 20GB
qm resize 105 scsi0 +18G
```

### 2. 添加额外网卡
```bash
qm set 105 --net1 virtio,bridge=vmbr1
```

### 3. 设置自动启动
```bash
qm set 105 --onboot 1 --startup order=1
```

### 4. 快照备份
```bash
qm snapshot 105 initial-setup --description "初始配置完成"
```

---

## ⚠️ 注意事项

1. **存储名称**：`nvme-dot`（NVMe 存储，已确认）
2. **网络桥接**：`vmbr0` 是默认桥接，如有自定义网桥需要修改
3. **SSH 公钥**：确保公钥格式正确，邮箱可替换为实际邮箱
4. **密码安全**：生产环境建议禁用密码登录，仅使用 SSH Key
5. **Cloud-Init 缓存**：如果修改 Cloud-Init 配置，需要清理 VM 内的缓存：
   ```bash
   rm -rf /var/lib/cloud/instances/*
   reboot
   ```

---

## 📚 参考资料

- Ubuntu Cloud Images: https://cloud-images.ubuntu.com/
- Proxmox VE Wiki: https://pve.proxmox.com/wiki/Main_Page
- Cloud-Init 文档: https://cloudinit.readthedocs.io/

---

*Created: 2026-03-01 22:00 (Asia/Shanghai)*
*Author: Molt 国王*
