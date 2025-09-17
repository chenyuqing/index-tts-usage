#!/bin/bash

# IndexTTS2 后台启动脚本
# 适用于 Mac mini M4

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录（绝对路径）
PROJECT_DIR="/Users/tim/Downloads/vibe-coding-local/Product/MVP/index-tts"
LOG_FILE="${PROJECT_DIR}/logs/indextts.log"
PID_FILE="${PROJECT_DIR}/logs/indextts.pid"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}   IndexTTS2 - 后台服务启动器${NC}"
echo -e "${BLUE}===========================================${NC}"

# 创建日志目录
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/outputs"

# 切换到项目目录
cd "${PROJECT_DIR}"

# 检查是否已有服务在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}检测到IndexTTS2服务已在运行 (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}是否要重启服务? (y/N): ${NC}"
        read -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}正在停止现有服务...${NC}"
            kill -TERM "$OLD_PID" 2>/dev/null || true
            sleep 3
            if kill -0 "$OLD_PID" 2>/dev/null; then
                kill -KILL "$OLD_PID" 2>/dev/null || true
            fi
            rm -f "$PID_FILE"
            echo -e "${GREEN}✓ 现有服务已停止${NC}"
        else
            echo -e "${YELLOW}保持现有服务运行，退出启动器${NC}"
            exit 0
        fi
    else
        rm -f "$PID_FILE"
    fi
fi

# 启动服务
echo -e "${GREEN}启动IndexTTS2后台服务...${NC}"

# 使用nohup在后台运行
nohup uv run webui.py --host 0.0.0.0 --port 7860 --verbose > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# 保存PID
echo $SERVER_PID > "$PID_FILE"

# 等待服务启动
echo -e "${BLUE}等待服务启动...${NC}"
sleep 5

# 检查服务状态
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}✓ IndexTTS2服务启动成功!${NC}"
    echo -e "${GREEN}  PID: $SERVER_PID${NC}"
    echo -e "${GREEN}  访问地址: http://127.0.0.1:7860${NC}"
    echo -e "${GREEN}  日志文件: $LOG_FILE${NC}"
    echo -e "${YELLOW}使用以下命令管理服务:${NC}"
    echo -e "${YELLOW}  停止服务: ./stop.sh${NC}"
    echo -e "${YELLOW}  查看日志: tail -f $LOG_FILE${NC}"
    echo -e "${YELLOW}  查看状态: ./status.sh${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo -e "${RED}请检查日志文件: $LOG_FILE${NC}"
    rm -f "$PID_FILE"
    exit 1
fi