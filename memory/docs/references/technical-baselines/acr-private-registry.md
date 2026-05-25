---
type: [KB:REFERENCE]
title: "阿里云 ACR 私人仓库配置手册"
created: 2026-03-04
updated: 2026-03-04
source: Manual
confidence: high
tags: [acr, aliyun, docker, registry, container]
related: [docker, ct110, node-11]
status: active
version: v1.0
last_verified: 2026-03-08
---

# 阿里云 ACR 私人仓库配置手册

## 基本信息

| 项目 | 值 |
|------|-----|
| **提供商** | 阿里云 (Alibaba Cloud) |
| **服务** | 容器镜像服务 ACR (Container Registry) |
| **类型** | 私人仓库 (Private Registry) |
| **用途** | 存储 Docker 镜像，供 CT110/node-11 使用 |

---

## 仓库地址

### Registry 地址

| 类型 | 地址 |
|------|------|
| **公网** | `registry.cn-hangzhou.aliyuncs.com` |
| **VPC 内网** | `registry-internal.cn-hangzhou.aliyuncs.com` |

### 命名空间

```
<your-namespace>/<repository-name>:<tag>
```

示例：
```
mycompany/backend:v1.0.0
```

---

## 认证方式

### 方式一：账号密码登录（推荐用于本地开发）

```bash
# 登录
docker login --username=<your-username> registry.cn-hangzhou.aliyuncs.com

# 输入密码（阿里云账号密码或访问凭证）
```

### 方式二：访问凭证登录（推荐用于服务器/自动化）

1. 登录阿里云控制台
2. 进入 **容器镜像服务 ACR** → **访问凭证**
3. 创建或复制 **长期访问凭证**
   - 用户名：通常是阿里云账号名
   - 密码：访问凭证密码

```bash
docker login --username=<credential-username> \
             --password=<credential-password> \
             registry.cn-hangzhou.aliyuncs.com
```

### 方式三：临时 Token（推荐用于 CI/CD）

```bash
# 获取临时 token（需要阿里云 CLI）
aliyun cr GetAuthorizationToken --region cn-hangzhou

# 使用 token 登录
docker login --username=<username> \
             --password=<temporary-token> \
             registry.cn-hangzhou.aliyuncs.com
```

> ⚠️ **注意**: 临时 token 有效期通常为 12 小时

---

## 常用命令

### 镜像推送

```bash
# 1. 打标签
docker tag <local-image>:<tag> registry.cn-hangzhou.aliyuncs.com/<namespace>/<repo>:<tag>

# 示例
docker tag myapp:latest registry.cn-hangzhou.aliyuncs.com/mycompany/myapp:v1.0.0

# 2. 推送
docker push registry.cn-hangzhou.aliyuncs.com/<namespace>/<repo>:<tag>

# 示例
docker push registry.cn-hangzhou.aliyuncs.com/mycompany/myapp:v1.0.0
```

### 镜像拉取

```bash
# 拉取镜像
docker pull registry.cn-hangzhou.aliyuncs.com/<namespace>/<repo>:<tag>

# 示例
docker pull registry.cn-hangzhou.aliyuncs.com/mycompany/myapp:v1.0.0
```

### 列出仓库镜像

```bash
# 使用阿里云 CLI
aliyun cr GetRepositoryTags \
  --RegionId cn-hangzhou \
  --RepoNamespace <namespace> \
  --RepoName <repo>
```

---

## Docker Compose 集成

### 方式一：使用 .docker/config.json

```bash
# 本地登录后，config.json 会自动保存凭证
# ~/.docker/config.json 内容示例
{
  "auths": {
    "registry.cn-hangzhou.aliyuncs.com": {
      "auth": "base64-encoded-credentials"
    }
  }
}
```

### 方式二：Docker Compose 指定凭证

```yaml
version: '3.8'

services:
  app:
    image: registry.cn-hangzhou.aliyuncs.com/mycompany/myapp:v1.0.0
    # Docker 会自动使用 ~/.docker/config.json 中的凭证
```

### 方式三：Kubernetes ImagePullSecrets

```yaml
# 1. 创建 secret
kubectl create secret docker-registry acr-secret \
  --docker-server=registry.cn-hangzhou.aliyuncs.com \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email>

# 2. 在 Pod 中引用
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: myapp
    image: registry.cn-hangzhou.aliyuncs.com/mycompany/myapp:v1.0.0
  imagePullSecrets:
  - name: acr-secret
```

---

## 服务器配置示例

### CT110 (Alpine Linux)

```bash
# 1. 安装 Docker（如果未安装）
apk add docker

# 2. 登录 ACR
docker login --username=<username> \
             --password=<password> \
             registry.cn-hangzhou.aliyuncs.com

# 3. 配置开机自动登录（可选）
# 将凭证保存到 /etc/docker/daemon.json
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://<your-mirror-id>.mirror.aliyuncs.com"
  ]
}
EOF

# 4. 重启 Docker
service docker restart
```

### node-11 (Ubuntu 24.04)

```bash
# 1. 登录 ACR
docker login --username=<username> \
             --password=<password> \
             registry.cn-hangzhou.aliyuncs.com

# 2. 配置 systemd 服务环境变量（可选）
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/acr-auth.conf << 'EOF'
[Service]
Environment="DOCKER_CONFIG=/root/.docker"
EOF

# 3. 重载并重启 Docker
systemctl daemon-reload
systemctl restart docker
```

---

## 镜像加速

### 阿里云镜像加速器

1. 登录阿里云控制台
2. 进入 **容器镜像服务** → **镜像加速器**
3. 获取加速器地址：`https://<your-id>.mirror.aliyuncs.com`

### 配置加速器

**Alpine Linux:**
```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://<your-id>.mirror.aliyuncs.com"
  ]
}
EOF
service docker restart
```

**Ubuntu:**
```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://<your-id>.mirror.aliyuncs.com"
  ]
}
EOF
systemctl restart docker
```

---

## 安全最佳实践

### 1. 使用访问凭证而非账号密码

- ✅ 长期访问凭证：可单独管理，可随时撤销
- ❌ 阿里云主账号密码：风险高，不应在服务器上使用

### 2. 最小权限原则

创建 RAM 用户并授予最小权限：
```
AliyunCRReadOnlyAccess  # 只读访问
AliyunCRFullAccess      # 完整访问
```

### 3. 定期轮换凭证

- 建议每 90 天更换一次访问凭证
- 旧凭证失效前更新所有服务器配置

### 4. 使用 VPC 内网（如果在阿里云）

```bash
# VPC 内网访问，更快且不计公网流量
docker pull registry-internal.cn-hangzhou.aliyuncs.com/<namespace>/<repo>:<tag>
```

---

## 故障排查

### 问题 1: authentication required

```bash
# 原因：未登录或凭证过期
# 解决：重新登录
docker login registry.cn-hangzhou.aliyuncs.com
```

### 问题 2: denied: requested access to the resource is denied

```bash
# 原因：权限不足
# 检查：
# 1. 确认仓库命名空间是否正确
# 2. 确认用户是否有该仓库的访问权限
# 3. 确认仓库是否为公开
```

### 问题 3: timeout / connection reset

```bash
# 原因：网络连接问题
# 解决：
# 1. 检查是否能访问阿里云
ping registry.cn-hangzhou.aliyuncs.com

# 2. 使用镜像加速器
# 3. 如果在境内，检查是否需要配置代理
```

---

## 相关文档

- **Docker 官方文档**: [docker.md](../docs/docker.md)
- **CT110 项目**: [ct110.md](../projects/ct110.md)
- **node-11 项目**: [node-11.md](../projects/node-11.md)

---

## 更新历史

- **2026-03-04**: 初始创建
