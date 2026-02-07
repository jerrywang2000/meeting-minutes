#!/bin/bash
# 该脚本启动前端开发服务器。

set -e

echo "🚀 正在启动前端服务..."

# 检查 pnpm
if ! command -v pnpm &> /dev/null; then
    echo "🟡 未找到 pnpm。正在通过 npm 全局安装 pnpm..."
    if ! command -v npm &> /dev/null; then
        echo "❌ 未安装 npm。请先安装 Node.js (其中包含 npm)。"
        exit 1
    fi
    npm install -g pnpm
    echo "✅ pnpm 已安装。"
else
    echo "✅ 已找到 pnpm。"
fi

echo "📂 正在进入 'frontend' 目录..."
if [ ! -d "frontend" ]; then
    echo "❌ 未找到 'frontend' 目录。请在项目的根目录运行此脚本。"
    exit 1
fi
cd frontend

echo "📦 正在安装依赖..."
pnpm install

echo "🌐 正在启动 Next.js 开发服务器..."
pnpm run dev
