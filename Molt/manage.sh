#!/bin/bash
# OpenClaw Molt 工作区管理脚本

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/Users/busiji/workbot/Molt"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 检查 Docker/OrbStack 是否运行
check_docker() {
    if ! docker info &> /dev/null; then
        echo_error "Docker/OrbStack 未运行"
        echo_info "请先启动 OrbStack 或 Docker Desktop"
        exit 1
    fi
    echo_success "Docker/OrbStack 运行正常"
}

# 首次安装（运行 onboarding）
onboard() {
    echo "======================================"
    echo "OpenClaw Molt - 首次安装"
    echo "======================================"
    echo ""

    check_docker

    cd "$PROJECT_DIR"

    echo_info "拉取最新镜像..."
    docker compose pull

    echo ""
    echo_info "开始 Onboarding（配置向导）..."
    echo_info "请按照提示完成配置："
    echo ""
    docker compose run --rm openclaw-cli onboard

    echo ""
    echo_success "Onboarding 完成！"
    echo ""
    echo_info "启动 Gateway..."
    docker compose up -d openclaw-gateway

    sleep 5

    echo ""
    echo_success "OpenClaw 启动成功！"
    echo ""
    echo_info "访问地址："
    echo "  - Gateway API: http://localhost:100"
    echo "  - 健康检查: http://localhost:100/healthz"
    echo ""
    echo_info "获取 Dashboard Token："
    echo "  docker compose run --rm openclaw-cli dashboard --no-open"
    echo ""
}

# 启动 OpenClaw
start() {
    echo "======================================"
    echo "启动 OpenClaw - Molt 工作区"
    echo "======================================"
    echo ""

    check_docker

    cd "$PROJECT_DIR"

    if [ ! -f "$PROJECT_DIR/config/openclaw.json" ]; then
        echo_error "配置文件不存在"
        echo_info "请先运行首次安装："
        echo "  ./manage.sh onboard"
        exit 1
    fi

    echo_info "启动容器..."
    docker compose up -d openclaw-gateway

    sleep 3

    echo ""
    echo_success "OpenClaw 启动成功！"
    echo ""
    echo_info "访问地址："
    echo "  - Gateway API: http://localhost:100"
    echo "  - 健康检查: http://localhost:100/healthz"
    echo "  - 模型列表: http://localhost:100/v1/models"
    echo ""
    echo_info "查看日志："
    echo "  docker compose logs -f"
    echo ""
    echo_info "停止服务："
    echo "  ./manage.sh stop"
    echo ""
}

# 停止 OpenClaw
stop() {
    echo_info "停止 OpenClaw..."
    cd "$PROJECT_DIR"
    docker compose down
    echo_success "OpenClaw 已停止"
}

# 重启 OpenClaw
restart() {
    stop
    echo ""
    start
}

# 查看日志
logs() {
    cd "$PROJECT_DIR"
    docker compose logs -f --tail=100 openclaw-gateway
}

# 查看状态
status() {
    cd "$PROJECT_DIR"
    docker compose ps
    echo ""
    echo_info "容器健康检查："
    curl -s http://localhost:100/healthz | jq '.' || echo_error "容器未运行或健康检查失败"
}

# 进入容器
shell() {
    cd "$PROJECT_DIR"
    docker compose exec openclaw-gateway bash
}

# 更新镜像
update() {
    echo_info "更新 OpenClaw 镜像..."
    cd "$PROJECT_DIR"
    docker compose pull
    echo_success "镜像更新完成"
    echo_info "运行 ./manage.sh restart 以应用更新"
}

# 备份工作区
backup() {
    BACKUP_FILE="workspace-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    echo_info "备份工作区到 $BACKUP_FILE..."
    tar -czf "$PROJECT_DIR/$BACKUP_FILE" -C "$PROJECT_DIR" workspace/ config/
    echo_success "备份完成: $PROJECT_DIR/$BACKUP_FILE"
}

# 获取 Dashboard Token
dashboard() {
    cd "$PROJECT_DIR"
    docker compose run --rm openclaw-cli dashboard --no-open
}

# 设备管理
devices() {
    cd "$PROJECT_DIR"
    case "${2:-list}" in
        list)
            docker compose run --rm openclaw-cli devices list
            ;;
        approve)
            if [ -z "${3:-}" ]; then
                echo_error "请提供设备 ID"
                echo "用法: ./manage.sh devices approve <device-id>"
                exit 1
            fi
            docker compose run --rm openclaw-cli devices approve "$3"
            ;;
        *)
            echo "用法: ./manage.sh devices {list|approve <id>}"
            exit 1
            ;;
    esac
}

# 主菜单
case "${1:-}" in
    onboard)
        onboard
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    shell)
        shell
        ;;
    update)
        update
        ;;
    backup)
        backup
        ;;
    dashboard)
        dashboard
        ;;
    devices)
        devices "$@"
        ;;
    *)
        echo "OpenClaw Molt 工作区管理"
        echo ""
        echo "用法: $0 {onboard|start|stop|restart|logs|status|shell|update|backup|dashboard|devices}"
        echo ""
        echo "命令："
        echo "  onboard  - 首次安装（运行配置向导）"
        echo "  start    - 启动 OpenClaw"
        echo "  stop     - 停止 OpenClaw"
        echo "  restart  - 重启 OpenClaw"
        echo "  logs     - 查看日志"
        echo "  status   - 查看状态"
        echo "  shell    - 进入容器"
        echo "  update   - 更新镜像"
        echo "  backup   - 备份工作区"
        echo "  dashboard- 获取 Dashboard Token"
        echo "  devices  - 设备管理（list/approve）"
        exit 1
        ;;
esac
