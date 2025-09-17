#!/bin/bash

# IndexTTS2 API Service Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/../:$PYTHONPATH"
export VIRTUAL_ENV="$SCRIPT_DIR/.venv"
export INDEX_TTS_API_PORT=${INDEX_TTS_API_PORT:-7861}
export INDEX_TTS_API_HOST=${INDEX_TTS_API_HOST:-0.0.0.0}

echo -e "${GREEN}🚀 Starting IndexTTS2 API Service${NC}"
echo -e "${YELLOW}=========================================${NC}"

# Check if virtual environment exists
if [ ! -d "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv "$VIRTUAL_ENV"
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source "$VIRTUAL_ENV/bin/activate"

# Install dependencies
echo -e "${YELLOW}📚 Installing dependencies...${NC}"
pip install -r requirements.txt

# Check if model checkpoints exist
if [ ! -d "../checkpoints" ]; then
    echo -e "${RED}❌ Error: Checkpoints directory not found at ../checkpoints${NC}"
    echo -e "${YELLOW}Please ensure IndexTTS2 models are downloaded${NC}"
    exit 1
fi

# Check if required model files exist
required_files=("config.yaml" "gpt.pth" "s2mel.pth" "bpe.model")
for file in "${required_files[@]}"; do
    if [ ! -f "../checkpoints/$file" ]; then
        echo -e "${RED}❌ Error: Required model file not found: ../checkpoints/$file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All model files found${NC}"

# Start the API service
echo -e "${GREEN}🎤 Starting API server on http://$INDEX_TTS_API_HOST:$INDEX_TTS_API_PORT${NC}"
echo -e "${YELLOW}📖 API documentation: http://localhost:$INDEX_TTS_API_PORT/docs${NC}"
echo -e "${YELLOW}⚡  Health check: http://localhost:$INDEX_TTS_API_PORT/health${NC}"
echo -e "${YELLOW}=========================================${NC}"

# Run the application
python app.py