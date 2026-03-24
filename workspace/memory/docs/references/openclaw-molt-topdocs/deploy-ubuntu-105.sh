#!/bin/bash
# Ubuntu 24.04 Cloud Image 部署脚本
# VM ID: 105
# 存储: nvme-dot
# 创建时间: 2026-03-01 22:13

set -e

echo "=== 开始部署 Ubuntu 24.04 Cloud Image (VM ID=105) ==="

# 1. 创建虚拟机
echo "[1/6] 创建虚拟机..."
qm create 105 --name "ubuntu-2404" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# 2. 导入磁盘
echo "[2/6] 导入磁盘镜像..."
qm importdisk 105 /var/lib/vz/template/iso/ubuntu-24.04-server-cloudimg-amd64.img nvme-dot

# 3. 挂载磁盘
echo "[3/6] 挂载磁盘..."
qm set 105 --scsihw virtio-scsi-pci --scsi0 nvme-dot:vm-105-disk-0

# 4. 设置启动盘
echo "[4/6] 设置启动盘..."
qm set 105 --boot c --bootdisk scsi0

# 5. 配置 Cloud-Init
echo "[5/6] 配置 Cloud-Init..."
cat > /tmp/user-data-105.yaml <<EOF
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
    - root:ubuntu2404
runcmd:
  - systemctl enable ssh
  - systemctl start ssh
EOF

# 生成 Cloud-Init ISO
cloud-localds /tmp/seed-105.iso /tmp/user-data-105.yaml

# 挂载 ISO
qm set 105 --cdrom local:iso/seed-105.iso

# 6. 配置网络（DHCP）
echo "[6/6] 配置网络（DHCP）..."
qm set 105 --ipconfig0 ip=dhcp

echo "=== 部署完成 ==="
echo "虚拟机 ID: 105"
echo "虚拟机名称: ubuntu-2404"
echo "默认密码: ubuntu2404"
echo "SSH 公钥已配置"
echo ""
echo "启动命令: qm start 105"
echo "连接命令: ssh root@<IP> (等待 1-2 分钟后)"
