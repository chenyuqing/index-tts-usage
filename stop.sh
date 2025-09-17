#!/bin/bash

# IndexTTS2 停止服务脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/Users/tim/Downloads/vibe-coding-local/Product/MVP/index-tts"
PID_FILE="${PROJECT_DIR}/logs/indextts.pid"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}     IndexTTS2 - 服务停止器${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查PID文件
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}未找到PID文件，尝试通过端口查找进程...${NC}"

    # 通过端口查找进程
    PORT_PID=$(lsof -ti:7860 2>/dev/null || true)
    if [ ! -z "$PORT_PID" ]; then
        echo -e "${BLUE}找到占用端口7860的进程 (PID: $PORT_PID)${NC}"
        echo -e "${BLUE}正在停止服务...${NC}"
        kill -TERM "$PORT_PID" 2>/dev/null || true
        sleep 3

        if kill -0 "$PORT_PID" 2>/dev/null; then
            echo -e "${YELLOW}温和终止失败，强制终止...${NC}"
            kill -KILL "$PORT_PID" 2>/dev/null || true
        fi
        echo -e "${GREEN}✓ 服务已停止${NC}"
    else
        echo -e "${YELLOW}未找到运行中的IndexTTS2服务${NC}"
    fi
    exit 0
fi

# 读取PID
SERVER_PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo -e "${YELLOW}进程 $SERVER_PID 不存在，清理PID文件${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

echo -e "${BLUE}正在停止IndexTTS2服务 (PID: $SERVER_PID)...${NC}"

# 温和终止
kill -TERM "$SERVER_PID" 2>/dev/null || true
echo -e "${BLUE}发送终止信号，等待进程结束...${NC}"

# 等待最多10秒
for i in {1..10}; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ 服务已成功停止${NC}"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo
echo -e "${YELLOW}温和终止超时，强制终止进程...${NC}"

# 强制终止
kill -KILL "$SERVER_PID" 2>/dev/null || true
sleep 1

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo -e "${GREEN}✓ 服务已强制停止${NC}"
    rm -f "$PID_FILE"
else
    echo -e "${RED}✗ 无法停止服务${NC}"
    exit 1
fi