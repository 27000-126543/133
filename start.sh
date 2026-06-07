#!/bin/bash

echo "=============================================="
echo "  企业资质证书管理系统 - 全栈启动脚本"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "[1/4] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python版本: $PYTHON_VERSION"

echo ""
echo "[2/4] 安装后端依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[3/4] 检查前端依赖..."
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    if ! command -v npm &> /dev/null; then
        echo "❌ 错误: 未找到npm，请先安装Node.js 18+"
        exit 1
    fi
    npm install
fi

echo ""
echo "[4/4] 启动服务..."
cd "$PROJECT_DIR"

echo ""
echo "=============================================="
echo "  启动后端服务 (端口: 8000)"
echo "=============================================="

cd "$PROJECT_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 3

echo ""
echo "=============================================="
echo "  启动前端服务 (端口: 5173)"
echo "=============================================="

cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=============================================="
echo "  服务启动完成！"
echo "=============================================="
echo ""
echo "后端API地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "前端地址: http://localhost:5173"
echo ""
echo "默认管理员账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "=============================================="

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
