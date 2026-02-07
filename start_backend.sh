#!/bin/bash
# 该脚本使用 Docker 启动后端服务。

set -e

echo "🚀 正在启动后端服务..."

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未安装 Docker。请先安装 Docker Desktop。"
    exit 1
fi
echo "✅ 已找到 Docker。"

echo "📂 正在进入 'backend' 目录..."
if [ ! -d "backend" ]; then
    echo "❌ 未找到 'backend' 目录。请在项目的根目录运行此脚本。"
    exit 1
fi
cd backend

echo "🛠️  正在构建 Docker 镜像 (首次运行可能需要一些时间)..."
./build-docker.sh cpu

echo "▶️  正在启动服务..."
echo "这将启动一个交互式设置，请根据提示选择一个模型。"
./run-docker.sh start --interactive

echo "🎉 后端服务应该已经开始运行。"
