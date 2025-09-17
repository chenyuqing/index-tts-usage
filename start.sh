#!/bin/bash

# IndexTTS2 启动脚本
# 适用于 Mac mini M4

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录（绝对路径）
PROJECT_DIR="/Users/tim/Downloads/vibe-coding-local/Product/MVP/index-tts"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}     IndexTTS2 - AI语音克隆系统启动器${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查当前目录
if [ ! -f "${PROJECT_DIR}/webui.py" ]; then
    echo -e "${RED}错误: 找不到webui.py文件${NC}"
    echo -e "${RED}请确保脚本在IndexTTS2项目目录中运行${NC}"
    exit 1
fi

# 切换到项目目录
cd "${PROJECT_DIR}"
echo -e "${GREEN}✓ 切换到项目目录: ${PROJECT_DIR}${NC}"

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo -e "${RED}错误: uv 未安装${NC}"
    echo -e "${YELLOW}请运行: pip install -U uv${NC}"
    exit 1
fi
echo -e "${GREEN}✓ uv 已安装${NC}"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${RED}错误: 虚拟环境不存在${NC}"
    echo -e "${YELLOW}请运行: uv sync --all-extras${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 虚拟环境已存在${NC}"

# 检查模型文件
echo -e "${BLUE}检查模型文件...${NC}"
required_files=("checkpoints/gpt.pth" "checkpoints/s2mel.pth" "checkpoints/bpe.model" "checkpoints/config.yaml")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}错误: 模型文件 $file 不存在${NC}"
        echo -e "${YELLOW}请运行以下命令下载模型:${NC}"
        echo -e "${YELLOW}modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ 所有模型文件存在${NC}"

# 检查GPU状态
echo -e "${BLUE}检查GPU加速状态...${NC}"
uv run tools/gpu_check.py

# 检查端口是否被占用
PORT=7860
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}"
    echo -e "${YELLOW}正在尝试终止占用进程...${NC}"

    # 尝试优雅终止
    PID=$(lsof -ti:$PORT)
    if [ ! -z "$PID" ]; then
        kill -TERM $PID 2>/dev/null || true
        sleep 2

        # 如果进程仍在运行，强制终止
        if kill -0 $PID 2>/dev/null; then
            kill -KILL $PID 2>/dev/null || true
            echo -e "${GREEN}✓ 已终止占用进程 (PID: $PID)${NC}"
        fi
    fi
else
    echo -e "${GREEN}✓ 端口 $PORT 可用${NC}"
fi

# 启动参数配置
HOST="0.0.0.0"
VERBOSE="--verbose"

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}启动 IndexTTS2 Web 界面...${NC}"
echo -e "${YELLOW}访问地址: http://127.0.0.1:$PORT${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo -e "${BLUE}===========================================${NC}"

# 创建输出目录
mkdir -p outputs

# 启动服务
exec uv run webui.py --host "$HOST" --port "$PORT" $VERBOSE