#!/bin/bash

echo "=============================================="
echo "  企业资质证书管理系统 - 前端启动脚本"
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR/frontend"

echo ""
echo "[1/2] 检查Node.js环境..."
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未找到npm，请先安装Node.js 18+"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js版本: $NODE_VERSION"

echo ""
echo "[2/2] 安装依赖并启动前端..."
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

echo ""
echo "=============================================="
echo "  前端服务启动中 (端口: 5173)"
echo "=============================================="
echo ""
echo "前端地址: http://localhost:5173"
echo ""
echo "确保后端服务已启动在 http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=============================================="

npm run dev
