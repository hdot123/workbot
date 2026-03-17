# PVE Ubuntu 24.04 Docker 黄金模板部署手册

> **用途**：在 Proxmox VE 中快速创建预装 Docker 的 Ubuntu 24.04 虚拟机模板
> **存储**：全部使用 `nvme-dot` 高速盘
> **VM ID**：9000
> **适用场景**：容器化应用、微服务架构、CI/CD Runner 节点

---

## 📋 环境规格

| 项目 | 规格 |
|------|------|
| 宿主机 | PVE 8.x |
| 存储池 | `nvme-dot` (系统盘 + Cloud-init 盘) |
| 基础镜像 | `ubuntu-24.04-server-cloudimg-amd64.img` |
| 网络 | `vmbr0` 桥接 |
| 硬件 | 2 vCPU (Host 模式) / 2GB RAM / 20GB Disk (Thin) |

---

## 🚀 部署流程

### 阶段一：PVE 宿主机端创建 VM

**执行位置**：PVE 宿主机 Shell (root 权限)

```bash
# ============================================
# 变量定义
# ============================================
VM_ID=9000
STORAGE=nvme-dot
IMG_NAME="ubuntu-24.04-server-cloudimg-amd64.img"

# ============================================
# 1. 创建 VM 基础配置
# ============================================
qm create $VM_ID \
    --name "u2404-docker-template" \
    --memory 2048 \
    --cores 2 \
    --cpu host \
    --net0 virtio,bridge=vmbr0

# ============================================
# 2. 导入镜像到高速盘
# ============================================
qm importdisk $VM_ID $IMG_NAME $STORAGE

# ============================================
# 3. 挂载磁盘 + SSD 优化 (discard)
# ============================================
qm set $VM_ID \
    --scsihw virtio-scsi-pci \
    --scsi0 $STORAGE:vm-$VM_ID-disk-0,discard=on

# ============================================
# 4. 在 nvme-dot 创建 Cloud-init 驱动器
# ============================================
qm set $VM_ID --ide2 $STORAGE:cloudinit

# ============================================
# 5. 引导顺序 + 序列控制台 (Cloud-init 必须)
# ============================================
qm set $VM_ID \
    --boot order=scsi0 \
    --serial0 socket \
    --vga serial0

# ============================================
# 6. 磁盘扩容到 20G
# ============================================
qm resize $VM_ID scsi0 +18G
```

**验证配置**：
```bash
qm config $VM_ID
```

---

### 阶段二：VM 内部环境固化

**执行位置**：虚拟机内部 (通过控制台或 SSH 登录，root 权限)

```bash
# ============================================
# 1. 替换为国内高速源 (Ubuntu 24.04 deb822 格式)
# ============================================
sed -i 's/archive.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/ubuntu.sources
sed -i 's/security.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/ubuntu.sources

# 更新软件包索引
apt-get update

# ============================================
# 2. 安装 Docker & Docker Compose (阿里云镜像)
# ============================================
# 安装依赖
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# 安装 Docker
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

# 启动 Docker
systemctl enable docker
systemctl start docker

# 验证安装
docker --version

# ============================================
# 3. 配置 Docker 镜像加速器
# ============================================
mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io",
    "https://hub-mirror.c.163.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# 重启 Docker
systemctl restart docker

# ============================================
# 4. 安装常用工具
# ============================================
apt-get install -y vim git wget curl htop net-tools tree jq bash-completion

# ============================================
# 5. 模板化清理 (克隆前必须执行)
# ============================================
# 清理 APT 缓存
apt-get autoremove -y
apt-get clean

# 清空 machine-id (克隆后会自动重新生成)
truncate -s 0 /etc/machine-id

# 删除 SSH 主机密钥 (克隆后会自动重新生成)
rm -f /etc/ssh/ssh_host_*

# 清理 Cloud-init 日志和缓存
cloud-init clean --logs --seed

# 清理临时文件
rm -rf /tmp/* /var/tmp/*

# 清理命令历史
history -c
rm -f ~/.bash_history
```

**验证 Docker**：
```bash
docker --version
docker compose version
docker run --rm hello-world
```

**退出虚拟机**：
```bash
exit
```

---

### 阶段三：固化为模板

**执行位置**：PVE 宿主机 Shell (root 权限)

```bash
# ============================================
# 1. 停止虚拟机
# ============================================
qm stop 9000

# ============================================
# 2. 转换为模板
# ============================================
qm template 9000
```

**验证模板**：
```bash
qm config 9000 | grep template
```

---

## 📦 后续使用：快速部署新虚拟机

### 方式一：命令行（推荐）

```bash
# ============================================
# 创建链接克隆 (秒级创建，节省空间)
# ============================================
qm clone 9000 1001 --name "my-docker-01" --full false

# ============================================
# 配置 Cloud-init (可选)
# ============================================
# 设置用户名
qm set 1001 --ciuser ubuntu

# 设置 SSH 公钥
qm set 1001 --sshkeys ~/.ssh/id_rsa.pub

# 设置网络 (DHCP)
qm set 1001 --ipconfig0 ip=dhcp

# ============================================
# 启动虚拟机
# ============================================
qm start 1001

# ============================================
# 查看 IP 地址 (等待 1-2 分钟)
# ============================================
qm guest exec 1001 -- ip addr show eth0

# 或者通过控制台查看
qm terminal 1001

# ============================================
# SSH 登录
# ============================================
ssh ubuntu@<VM_IP>
```

### 方式二：PVE Web UI

1. 右键点击模板 `9000`
2. 选择 **Clone** → **Linked Clone**
3. 设置新 VM ID 和名称
4. 在 **Cloud-Init** 选项卡配置：
   - User: `ubuntu`
   - SSH public key: 粘贴你的公钥
   - IP config: `ip=dhcp`
5. 启动虚拟机
6. 通过 SSH 登录

---

## 🔑 Cloud-init 配置模板

如果需要自定义初始化配置，可以在 PVE 面板的 **Cloud-Init** 选项卡设置：

### 基础配置示例

```yaml
# 用户名
ciuser: ubuntu

# SSH 公钥
sshkeys: |
  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... your@email.com

# 网络配置
ipconfig0: ip=dhcp
# 或者静态 IP
# ipconfig0: ip=192.168.1.100/24,gw=192.168.1.1

# DNS
nameserver: 8.8.8.8

# 搜索域
searchdomain: local
```

### 高级配置（通过 snippets）

创建文件 `/var/lib/vz/snippets/user-data.yaml`：

```yaml
#cloud-config
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC...
    groups:
      - docker
      - sudo

hostname: docker-node-01
timezone: Asia/Shanghai

package_update: true
package_upgrade: true

packages:
  - vim
  - git
  - htop

runcmd:
  - docker pull nginx:alpine
  - docker pull redis:alpine
  - echo "Cloud-init completed at $(date)" >> /var/log/cloud-init.log
```

应用到虚拟机：
```bash
qm set 1001 --cicustom "user=local:snippets/user-data.yaml"
```

---

## ⚙️ 关键技术点

| 技术点 | 说明 |
|--------|------|
| **存储策略** | 全部使用 `nvme-dot` 高速盘（系统盘 + Cloud-init 盘） |
| **磁盘优化** | 启用 `discard=on` 支持 SSD TRIM，提升性能 |
| **网络配置** | 使用 `virtio` 网卡 + `vmbr0` 桥接，性能最优 |
| **Cloud-init** | 必须配置 `serial0 socket` + `vga serial0` 才能正常工作 |
| **模板清理** | 清空 machine-id 和 SSH host keys，避免克隆冲突 |
| **Docker 加速** | 使用国内镜像源（百度云、DaoCloud、163）提升拉取速度 |
| **克隆方式** | 推荐 Linked Clone（链接克隆），秒级创建 + 节省空间 |

---

## 🛠️ 常见问题

### 1. Cloud-init 不执行？

**检查配置**：
```bash
qm config 9000 | grep serial
```

必须包含：
```
serial0: socket
vga: serial0
```

### 2. 克隆后无法 SSH 登录？

**原因**：Cloud-init 未执行或 SSH 公钥未配置

**解决**：
```bash
# 检查 Cloud-init 日志
qm terminal 1001
# 在虚拟机内执行
cat /var/log/cloud-init-output.log

# 手动配置 SSH
qm set 1001 --sshkeys ~/.ssh/id_rsa.pub
```

### 3. Docker 镜像拉取慢？

**验证加速器**：
```bash
docker info | grep "Registry Mirrors" -A 5
```

**手动拉取测试**：
```bash
time docker pull nginx:alpine
```

### 4. 磁盘空间不足？

**检查存储池**：
```bash
pvesm status
```

**扩展虚拟机磁盘**：
```bash
qm resize 1001 scsi0 +10G
```

### 5. 如何删除模板？

```bash
# 模板不能直接删除，需要先转换为虚拟机
qm set 9000 --template 0

# 然后删除
qm destroy 9000
```

---

## 📚 参考资源

- [Proxmox VE 官方文档](https://pve.proxmox.com/wiki/Main_Page)
- [Ubuntu Cloud Images](https://cloud-images.ubuntu.com/)
- [Cloud-init 官方文档](https://cloudinit.readthedocs.io/)
- [Docker 官方文档](https://docs.docker.com/)

---

## 📝 维护记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-10 | v1.0 | 初始版本，基于 Ubuntu 24.04 + Docker |

---

**文档维护**：此文档已保存至项目记忆系统，可通过 AI 助手快速查阅和更新。
