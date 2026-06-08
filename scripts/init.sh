#!/usr/bin/env bash
# =============================================================================
# 期货自动进化因子挖掘系统 - 初始化脚本
# =============================================================================
# 用法:
#   ./scripts/init.sh              # 完整初始化
#   ./scripts/init.sh --skip-db    # 跳过数据库初始化
#   ./scripts/init.sh --dev        # 开发模式 (带热重载)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKIP_DB=false
DEV_MODE=false

# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [--skip-db] [--dev]"
            echo "  --skip-db    跳过数据库初始化"
            echo "  --dev        开发模式 (启用热重载)"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# 颜色输出
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# 检查依赖
# ---------------------------------------------------------------------------
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
    log_ok "$1 已安装"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
echo "============================================================================="
echo "  期货自动进化因子挖掘系统 - 初始化"
echo "============================================================================="

# 检查 Docker
check_dependency docker
check_dependency docker-compose

# 创建必要目录
log_info "创建数据目录..."
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/logs"
log_ok "数据目录已创建"

# 检查 .env 文件
if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
    log_warn ".env 文件不存在，从模板创建..."
    cp "$PROJECT_ROOT/backend/.env.example" "$PROJECT_ROOT/.env"
    log_ok ".env 已创建，请根据需要修改配置"
else
    log_ok ".env 已存在"
fi

# 拉取镜像
log_info "拉取基础镜像..."
docker-compose -f "$PROJECT_ROOT/docker-compose.yml" pull
docker-compose -f "$PROJECT_ROOT/docker-compose.yml" build
log_ok "镜像构建完成"

# 启动基础设施服务
if [[ "$SKIP_DB" == false ]]; then
    log_info "启动基础设施服务 (TimescaleDB + Redis)..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d timescaledb redis

    # 等待数据库就绪
    log_info "等待数据库就绪..."
    for i in {1..30}; do
        if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T timescaledb \
            pg_isready -U "${POSTGRES_USER:-qmt}" -d "${POSTGRES_DB:-quant_db}" &>/dev/null; then
            log_ok "TimescaleDB 已就绪"
            break
        fi
        sleep 1
        echo -n "."
    done

    # 等待 Redis 就绪
    log_info "等待 Redis 就绪..."
    for i in {1..30}; do
        if docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -T redis \
            redis-cli -a "${REDIS_PASSWORD:-qmt_redis_secret}" ping &>/dev/null; then
            log_ok "Redis 已就绪"
            break
        fi
        sleep 1
        echo -n "."
    done

    # 执行数据库初始化
    log_info "执行数据库初始化..."
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" run --rm init
    log_ok "数据库初始化完成"
else
    log_warn "跳过数据库初始化"
fi

# 启动所有服务
log_info "启动所有服务..."
if [[ "$DEV_MODE" == true ]]; then
    log_info "开发模式: 启用热重载"
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d
    # 开发模式下 backend 使用热重载
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" exec -d backend \
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d
fi

# 等待服务就绪
log_info "等待服务就绪..."
sleep 5

# 健康检查
log_info "执行健康检查..."
HEALTH_STATUS=0

# 检查后端
if curl -sf http://localhost:8000/health &>/dev/null; then
    log_ok "后端服务健康 (http://localhost:8000)"
else
    log_error "后端服务未通过健康检查"
    HEALTH_STATUS=1
fi

# 检查前端
if curl -sf http://localhost/health &>/dev/null; then
    log_ok "前端服务健康 (http://localhost)"
else
    log_warn "前端服务健康检查失败，可能仍在启动中"
fi

echo ""
echo "============================================================================="
if [[ $HEALTH_STATUS -eq 0 ]]; then
    echo -e "${GREEN}初始化完成！系统已就绪${NC}"
    echo ""
    echo "  前端界面: http://localhost"
    echo "  后端 API: http://localhost:8000"
    echo "  API 文档: http://localhost:8000/docs"
    echo "  健康检查: http://localhost:8000/health"
    echo ""
    echo "常用命令:"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
else
    echo -e "${YELLOW}初始化完成，但部分服务未通过健康检查${NC}"
    echo "请查看日志: docker-compose logs -f"
fi
echo "============================================================================="

exit $HEALTH_STATUS
