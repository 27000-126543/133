#!/bin/bash

echo "=============================================="
echo "  企业资质证书管理系统 - 后端启动脚本"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "[1/3] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.9+"
    exit 1
fi

echo ""
echo "[2/3] 激活虚拟环境并安装依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[3/3] 启动后端服务..."
cd "$PROJECT_DIR/backend"

echo ""
echo "=============================================="
echo "  后端服务启动中 (端口: 8000)"
echo "=============================================="
echo ""
echo "API地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "默认管理员账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=============================================="

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
