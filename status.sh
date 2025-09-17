#!/bin/bash

# IndexTTS2 服务状态查看脚本

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
LOG_FILE="${PROJECT_DIR}/logs/indextts.log"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}     IndexTTS2 - 服务状态检查${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查端口占用
PORT_STATUS=""
if lsof -Pi :7860 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PORT_PID=$(lsof -ti:7860)
    PORT_STATUS="${GREEN}端口7860已监听 (PID: $PORT_PID)${NC}"
else
    PORT_STATUS="${RED}端口7860未被监听${NC}"
fi

# 检查PID文件
if [ -f "$PID_FILE" ]; then
    SERVER_PID=$(cat "$PID_FILE")
    echo -e "${BLUE}PID文件存在: $SERVER_PID${NC}"

    # 检查进程是否运行
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        echo -e "${GREEN}✓ IndexTTS2服务正在运行 (PID: $SERVER_PID)${NC}"

        # 检查进程详细信息
        echo -e "${BLUE}进程信息:${NC}"
        ps -p "$SERVER_PID" -o pid,ppid,cmd,etime,pmem,pcpu 2>/dev/null || echo "无法获取进程详细信息"

        # 内存使用
        if command -v top >/dev/null 2>&1; then
            MEMORY_USAGE=$(top -pid "$SERVER_PID" -l 1 -s 0 2>/dev/null | grep -E "^[0-9]" | awk '{print $8}' || echo "N/A")
            echo -e "${BLUE}内存使用: $MEMORY_USAGE${NC}"
        fi
    else
        echo -e "${RED}✗ PID文件存在但进程未运行${NC}"
        echo -e "${YELLOW}建议清理PID文件: rm $PID_FILE${NC}"
    fi
else
    echo -e "${YELLOW}PID文件不存在${NC}"
fi

# 端口状态
echo -e "${BLUE}端口状态: $PORT_STATUS${NC}"

# Web服务状态检查
echo -e "${BLUE}Web服务状态检查...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7860 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Web界面响应正常 (HTTP $HTTP_STATUS)${NC}"
    echo -e "${GREEN}  访问地址: http://127.0.0.1:7860${NC}"
elif [ "$HTTP_STATUS" = "000" ]; then
    echo -e "${RED}✗ Web界面无响应 (连接失败)${NC}"
else
    echo -e "${YELLOW}⚠ Web界面异常响应 (HTTP $HTTP_STATUS)${NC}"
fi

# GPU状态检查
echo -e "${BLUE}GPU状态检查...${NC}"
cd "$PROJECT_DIR"
if [ -f "tools/gpu_check.py" ]; then
    uv run tools/gpu_check.py 2>/dev/null | grep -E "(MPS|CUDA)" || echo -e "${YELLOW}GPU状态检查失败${NC}"
else
    echo -e "${YELLOW}GPU检查工具不存在${NC}"
fi

# 日志文件信息
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(ls -lh "$LOG_FILE" | awk '{print $5}')
    LOG_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "N/A")
    echo -e "${BLUE}日志文件: $LOG_FILE${NC}"
    echo -e "${BLUE}  大小: $LOG_SIZE, 行数: $LOG_LINES${NC}"

    echo -e "${BLUE}最近的日志 (最后10行):${NC}"
    echo -e "${YELLOW}$(tail -n 10 "$LOG_FILE" 2>/dev/null)${NC}"
else
    echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
fi

echo -e "${BLUE}===========================================${NC}"

# 输出管理命令提示
echo -e "${BLUE}管理命令:${NC}"
echo -e "${YELLOW}  启动服务: ./start.sh 或 ./start_background.sh${NC}"
echo -e "${YELLOW}  停止服务: ./stop.sh${NC}"
echo -e "${YELLOW}  查看日志: tail -f $LOG_FILE${NC}"