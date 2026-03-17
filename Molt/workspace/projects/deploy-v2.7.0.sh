#!/bin/bash
# ClawRouter v2.7.0 快速部署脚本
# 用法: bash deploy-v2.7.0.sh

set -e

# ============================================
# 配置区域（请根据实际情况修改）
# ============================================
REMOTE_USER="user"                          # SSH 用户名
REMOTE_HOST="192.168.88.27"                 # 远程服务器 IP
REMOTE_DIR="/opt/clawrouter"                # 远程部署目录
LOCAL_DIR="/Users/busiji/passkills/tmp/clawrouter-deploy"  # 本地代码目录

# ============================================
# 颜色输出
# ============================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# ============================================
# 步骤 1: 部署前检查
# ============================================
echo ""
echo "======================================"
echo "ClawRouter v2.7.0 快速部署"
echo "======================================"
echo ""

echo_info "步骤 1/7: 部署前检查..."

# 检查本地代码
if [ ! -f "$LOCAL_DIR/src/server.js" ]; then
    echo_error "本地代码不存在: $LOCAL_DIR/src/server.js"
    exit 1
fi

VERSION=$(head -15 "$LOCAL_DIR/src/server.js" | grep -o "v2\.7\.0" || echo "")
if [ "$VERSION" != "v2.7.0" ]; then
    echo_error "本地代码版本不是 v2.7.0"
    exit 1
fi
echo_success "本地代码版本: v2.7.0"

# 检查远程连接
echo_info "检查远程连接..."
if ! ssh -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo ok" &>/dev/null; then
    echo_error "无法连接到远程服务器 $REMOTE_USER@$REMOTE_HOST"
    exit 1
fi
echo_success "远程连接正常"

# 检查远程服务当前版本
CURRENT_VERSION=$(ssh "$REMOTE_USER@$REMOTE_HOST" "curl -s http://localhost:3000/health | jq -r '.version'")
echo_info "远程服务当前版本: $CURRENT_VERSION"

# ============================================
# 步骤 2: 备份
# ============================================
echo ""
echo_info "步骤 2/7: 备份当前版本..."

ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
    cd $REMOTE_DIR
    mkdir -p backups/v2.6.0
    cp src/server.js backups/v2.6.0/ 2>/dev/null || true
    cp src/protocol-adapter.js backups/v2.6.0/ 2>/dev/null || true
    cp .env backups/v2.6.0/ 2>/dev/null || true
    ls -lh backups/v2.6.0/
EOF

echo_success "备份完成"

# ============================================
# 步骤 3: 上传新版本
# ============================================
echo ""
echo_info "步骤 3/7: 上传新版本代码..."

rsync -avz --progress \
    "$LOCAL_DIR/src/server.js" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/src/"

rsync -avz --progress \
    "$LOCAL_DIR/src/protocol-adapter.js" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/src/"

echo_success "代码上传完成"

# ============================================
# 步骤 4: 检查环境变量
# ============================================
echo ""
echo_info "步骤 4/7: 检查环境变量..."

ENV_CHECK=$(ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
    cd $REMOTE_DIR
    if [ -f .env ]; then
        grep "DASHSCOPE_API_KEY" .env || echo "NOT_FOUND"
    else
        echo "NO_ENV_FILE"
    fi
EOF
)

if [ "$ENV_CHECK" == "NOT_FOUND" ] || [ "$ENV_CHECK" == "NO_ENV_FILE" ]; then
    echo_error "未找到 DASHSCOPE_API_KEY 配置"
    echo_info "请手动配置环境变量后再继续"
    echo_info "示例："
    echo "  ssh $REMOTE_USER@$REMOTE_HOST"
    echo "  cd $REMOTE_DIR"
    echo "  echo 'DASHSCOPE_API_KEY=sk-xxx' >> .env"
    echo ""
    read -p "配置完成后按回车继续..."
fi

echo_success "环境变量检查完成"

# ============================================
# 步骤 5: 重启服务
# ============================================
echo ""
echo_info "步骤 5/7: 重启服务..."

echo_info "检测服务管理方式..."
SERVICE_TYPE=$(ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
    cd $REMOTE_DIR
    if [ -f docker-compose.yml ]; then
        echo "docker"
    elif command -v pm2 &> /dev/null && pm2 list | grep -q clawrouter; then
        echo "pm2"
    elif systemctl is-active --quiet clawrouter 2>/dev/null; then
        echo "systemd"
    else
        echo "manual"
    fi
EOF
)

echo_info "检测到服务类型: $SERVICE_TYPE"

case $SERVICE_TYPE in
    docker)
        echo_info "使用 Docker Compose 重启..."
        ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
            cd $REMOTE_DIR
            docker compose restart
EOF
        ;;
    pm2)
        echo_info "使用 PM2 重启..."
        ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
            pm2 restart clawrouter
EOF
        ;;
    systemd)
        echo_info "使用 systemd 重启..."
        ssh "$REMOTE_USER@$REMOTE_HOST" <<EOF
            sudo systemctl restart clawrouter
EOF
        ;;
    manual)
        echo_error "检测到手动管理进程，请手动重启"
        echo_info "找到进程 PID 并 kill，然后重新启动 node src/server.js"
        read -p "手动重启完成后按回车继续..."
        ;;
esac

echo_success "服务重启完成"

# ============================================
# 步骤 6: 等待服务启动
# ============================================
echo ""
echo_info "步骤 6/7: 等待服务启动..."

for i in {1..30}; do
    sleep 1
    if ssh "$REMOTE_USER@$REMOTE_HOST" "curl -s http://localhost:3000/health" &>/dev/null; then
        echo_success "服务已启动（${i}s）"
        break
    fi
    echo -n "."
done

echo ""

# ============================================
# 步骤 7: 验证部署
# ============================================
echo ""
echo_info "步骤 7/7: 验证部署..."

# 检查版本
NEW_VERSION=$(ssh "$REMOTE_USER@$REMOTE_HOST" "curl -s http://localhost:3000/health | jq -r '.version'")
if [ "$NEW_VERSION" == "2.7.0" ]; then
    echo_success "版本验证通过: $NEW_VERSION"
else
    echo_error "版本验证失败: 预期 2.7.0，实际 $NEW_VERSION"
    exit 1
fi

# 检查 aliyun-embedding
MODEL_COUNT=$(ssh "$REMOTE_USER@$REMOTE_HOST" "curl -s http://localhost:3000/v1/models | jq '[.data[] | select(.id == \"aliyun-embedding\")] | length'")
if [ "$MODEL_COUNT" == "1" ]; then
    echo_success "aliyun-embedding 模型已暴露"
else
    echo_error "aliyun-embedding 模型未找到"
    exit 1
fi

# 测试 embedding
EMBEDDING_TEST=$(ssh "$REMOTE_USER@$REMOTE_HOST" <<'EOF'
    curl -s http://localhost:3000/v1/embeddings \
        -H "Content-Type: application/json" \
        -d '{"model": "aliyun-embedding", "input": "测试"}' \
        | jq '{model, count: (.data | length), dim: (.data[0].embedding | length)}'
EOF
)

MODEL=$(echo "$EMBEDDING_TEST" | jq -r '.model')
COUNT=$(echo "$EMBEDDING_TEST" | jq -r '.count')
DIM=$(echo "$EMBEDDING_TEST" | jq -r '.dim')

if [ "$MODEL" == "aliyun-embedding" ] && [ "$COUNT" == "1" ] && [ "$DIM" == "1024" ]; then
    echo_success "Embedding 测试通过"
else
    echo_error "Embedding 测试失败: $EMBEDDING_TEST"
    exit 1
fi

# ============================================
# 部署完成
# ============================================
echo ""
echo "======================================"
echo_success "部署完成！"
echo "======================================"
echo ""
echo_info "服务地址: http://$REMOTE_HOST:3000"
echo_info "健康检查: curl http://$REMOTE_HOST:3000/health"
echo_info "完整测试: bash /tmp/clawrouter-v2.7.0-test.sh"
echo ""
echo_info "回滚命令（如需）:"
echo "  ssh $REMOTE_USER@$REMOTE_HOST"
echo "  cd $REMOTE_DIR"
echo "  cp backups/v2.6.0/* src/"
echo "  docker compose restart  # 或 pm2 restart clawrouter"
echo ""
