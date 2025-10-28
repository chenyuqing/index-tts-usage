#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

cd "${PROJECT_ROOT}"

if ! command -v uv >/dev/null 2>&1; then
  echo "[启动器] 未检测到 uv，请先安装：https://docs.astral.sh/uv/"
  exit 1
fi

echo "[启动器] 启动自动配音 Web 控制台..."
echo "访问地址: http://127.0.0.1:5005"

uv run python webui_auto_voiceover.py
