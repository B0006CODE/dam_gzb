#!/bin/bash

# Smart Water 项目快速部署脚本 - Linux/macOS 版本
# 用法: ./deploy.sh [start|stop|restart|status|logs|clean|start-prod|stop-prod|restart-prod|status-prod|logs-prod]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印彩色消息
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

show_help() {
    print_color $CYAN "\n=== Smart Water 快速部署脚本 ===\n"
    echo "用法: ./deploy.sh [命令] [选项]"
    echo ""
    echo "可用命令:"
    echo "  start      - 启动基础服务（默认）"
    echo "  start-all  - 启动所有服务（包含 GPU 服务）"
    echo "  start-prod - 启动生产模式服务"
    echo "  stop       - 停止所有服务"
    echo "  stop-prod  - 停止生产模式服务"
    echo "  restart    - 重启所有服务"
    echo "  restart-prod - 重启生产模式服务"
    echo "  status     - 查看服务状态"
    echo "  status-prod - 查看生产模式服务状态"
    echo "  logs       - 查看服务日志"
    echo "  logs-prod  - 查看生产模式服务日志"
    echo "  clean      - 停止并清除所有数据（⚠️ 危险操作）"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh              # 启动基础服务"
    echo "  ./deploy.sh start-all    # 启动包含 GPU 的所有服务"
    echo "  ./deploy.sh start-prod   # 以生产模式启动服务"
    echo "  ./deploy.sh status       # 查看服务状态"
    echo "  ./deploy.sh logs         # 查看日志"
    echo ""
}

compose_cmd() {
    local production=$1
    local include_gpu=$2
    local cmd=(docker compose)

    if [ "$production" = "true" ]; then
        cmd+=(-f docker-compose.yml -f docker-compose.prod.yml)
    else
        cmd+=(-f docker-compose.yml -f docker-compose.dev.yml)
    fi
    if [ "$include_gpu" = "true" ]; then
        cmd+=(--profile all)
    fi

    printf '%q ' "${cmd[@]}"
}

check_prerequisites() {
    print_color $YELLOW "\n🔍 检查系统要求..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_color $RED "✗ 错误: 未找到 Docker，请先安装 Docker"
        echo "  安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_color $GREEN "✓ Docker: $(docker --version)"
    
    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        print_color $RED "✗ 错误: Docker Compose 不可用"
        exit 1
    fi
    print_color $GREEN "✓ Docker Compose: $(docker compose version)"
    
    # 检查 Docker 服务是否运行
    if ! docker ps &> /dev/null; then
        print_color $RED "✗ 错误: Docker 服务未运行，请启动 Docker"
        exit 1
    fi
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        print_color $YELLOW "\n⚠️  未找到 .env 文件"
        if [ -f ".env.template" ]; then
            read -p "是否从 .env.template 创建 .env 文件？[Y/n] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                cp .env.template .env
                print_color $GREEN "✓ 已创建 .env 文件，请编辑并配置必要的环境变量"
                print_color $YELLOW "  至少需要配置一个 LLM API Key（如 SILICONFLOW_API_KEY）"
                echo ""
                read -p "按 Enter 继续..."
            fi
        else
            print_color $RED "✗ 错误: 未找到 .env.template 文件"
            exit 1
        fi
    else
        print_color $GREEN "✓ .env 文件存在"
    fi
    
    print_color $GREEN "✓ 系统要求检查通过\n"
}

start_services() {
    local include_gpu=$1
    local production=$2
    
    check_prerequisites
    
    if [ "$production" = "true" ]; then
        print_color $CYAN "\n🚀 启动生产模式服务..."
        eval "$(compose_cmd "$production" "$include_gpu") up --build -d"
    elif [ "$include_gpu" = "true" ]; then
        print_color $CYAN "\n🚀 启动所有服务（包含 GPU 服务）..."
        print_color $YELLOW "⚠️  GPU 服务需要 NVIDIA GPU 和 nvidia-container-toolkit"
        eval "$(compose_cmd "$production" "$include_gpu") up --build -d"
    else
        print_color $CYAN "\n🚀 启动基础服务..."
        eval "$(compose_cmd "$production" "$include_gpu") up --build -d"
    fi
    
    if [ $? -eq 0 ]; then
        print_color $GREEN "\n✓ 服务启动成功！"
        print_color $YELLOW "\n⏱️  首次启动需要 5-10 分钟来下载镜像和初始化数据库"
        if [ "$production" = "true" ]; then
            print_color $YELLOW "   请使用 './deploy.sh status-prod' 检查服务状态\n"
        else
            print_color $YELLOW "   请使用 './deploy.sh status' 检查服务状态\n"
        fi
        
        print_color $CYAN "📋 访问地址:"
        if [ "$production" = "true" ]; then
            echo "  前端界面:    http://localhost:80"
            echo "  API 健康检查: http://localhost:5050/api/system/health"
        else
            echo "  前端界面:    http://localhost:5173"
            echo "  API 文档:    http://localhost:5050/docs"
        fi
        echo "  Neo4j 浏览器: http://localhost:7474"
        echo "  MinIO 控制台: http://localhost:9001"
        echo ""
    else
        print_color $RED "\n✗ 服务启动失败，请查看日志: ./deploy.sh logs"
        exit 1
    fi
}

stop_services() {
    local production=$1
    if [ "$production" = "true" ]; then
        print_color $YELLOW "\n🛑 停止生产模式服务..."
    else
        print_color $YELLOW "\n🛑 停止所有服务..."
    fi
    eval "$(compose_cmd "$production" false) down"
    
    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ 服务已停止\n"
    fi
}

restart_services() {
    local production=$1
    if [ "$production" = "true" ]; then
        print_color $YELLOW "\n🔄 重启生产模式服务..."
    else
        print_color $YELLOW "\n🔄 重启所有服务..."
    fi
    eval "$(compose_cmd "$production" false) restart"
    
    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ 服务已重启\n"
        show_status "$production"
    fi
}

show_status() {
    local production=${1:-false}
    print_color $CYAN "\n📊 服务状态:"
    eval "$(compose_cmd "$production" false) ps"
    
    print_color $CYAN "\n💾 磁盘使用:"
    docker system df
}

show_logs() {
    local production=${1:-false}
    print_color $CYAN "\n📜 服务日志 (Ctrl+C 退出):"
    eval "$(compose_cmd "$production" false) logs -f --tail=100"
}

clean_all() {
    print_color $RED "\n⚠️  警告: 这将删除所有容器、网络和数据卷！"
    read -p "所有数据将被永久删除，是否继续？[y/N] " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_color $YELLOW "\n🧹 清理所有数据..."
        docker compose down -v
        
        if [ -d "docker/volumes" ]; then
            print_color $YELLOW "删除本地数据目录..."
            rm -rf docker/volumes
        fi
        
        print_color $GREEN "✓ 清理完成\n"
    else
        print_color $YELLOW "✗ 已取消\n"
    fi
}

# 主逻辑
ACTION=${1:-start}

case $ACTION in
    start)
        start_services false false
        ;;
    start-all)
        start_services true false
        ;;
    start-prod)
        start_services false true
        ;;
    stop)
        stop_services false
        ;;
    stop-prod)
        stop_services true
        ;;
    restart)
        restart_services false
        ;;
    restart-prod)
        restart_services true
        ;;
    status)
        show_status false
        ;;
    status-prod)
        show_status true
        ;;
    logs)
        show_logs false
        ;;
    logs-prod)
        show_logs true
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_color $RED "错误: 未知命令 '$ACTION'"
        show_help
        exit 1
        ;;
esac
