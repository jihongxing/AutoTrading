#!/bin/bash
# BTC 自动交易系统 - 启动脚本

set -e

MODE=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

case $MODE in
    dev)
        echo "启动开发环境..."
        docker-compose -f docker-compose.dev.yml up -d
        echo "等待服务启动..."
        sleep 10
        echo "初始化 QuestDB 表..."
        curl -s -G --data-urlencode "query=$(cat scripts/init_questdb.sql)" http://localhost:9000/exec || true
        echo ""
        echo "服务已启动:"
        echo "  - API: http://localhost:8000"
        echo "  - QuestDB: http://localhost:9000"
        echo "  - Kafka: localhost:9092"
        ;;
    prod)
        echo "启动生产环境..."
        docker-compose up -d
        echo "等待服务启动..."
        sleep 15
        echo "初始化 QuestDB 表..."
        curl -s -G --data-urlencode "query=$(cat scripts/init_questdb.sql)" http://localhost:9000/exec || true
        echo ""
        echo "服务已启动"
        ;;
    stop)
        echo "停止服务..."
        docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
        docker-compose down 2>/dev/null || true
        echo "服务已停止"
        ;;
    logs)
        docker-compose logs -f
        ;;
    *)
        echo "用法: $0 {dev|prod|stop|logs}"
        exit 1
        ;;
esac
