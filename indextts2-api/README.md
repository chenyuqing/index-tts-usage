# IndexTTS2 API Service

一个简化的 IndexTTS2 语音克隆和 TTS RESTful API 微服务。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd indextts2-api
./start.sh
```

### 2. 启动服务

```bash
# 使用启动脚本（推荐）
./start.sh

# 或手动启动
python app.py
```

服务将在 `http://localhost:7861` 启动。

### 3. API 文档

- Swagger UI: http://localhost:7861/docs
- ReDoc: http://localhost:7861/redoc

## 📋 API 端点

### 健康检查
```bash
GET /health
GET /api/v1/health
```

### 模型信息
```bash
GET /api/v1/models
```

### 语音合成
```bash
POST /api/v1/tts
Content-Type: application/json

{
  "text": "你好，世界！",
  "language": "zh",
  "speed": 1.0,
  "pitch": 1.0
}
```

### 声音克隆
```bash
POST /api/v1/clone-voice
Content-Type: multipart/form-data

text: "这是克隆的声音"
reference_audio: [audio file]
language: "zh"
speed: 1.0
pitch: 1.0
```

### 声音分析
```bash
POST /api/v1/analyze-voice
Content-Type: multipart/form-data

reference_audio: [audio file]
```

## 🛠️ 配置

### 环境变量

```bash
INDEX_TTS_API_HOST=0.0.0.0
INDEX_TTS_API_PORT=7861
```

### 配置文件

配置文件位于 `config/settings.py`，可以修改以下参数：

- `HOST`: 服务主机地址
- `PORT`: 服务端口
- `CHECKPOINT_DIR`: 模型检查点目录
- `USE_HALF_PRECISION`: 是否使用半精度
- `DEVICE`: 计算设备（auto/cpu/cuda）

## 🧪 测试

运行集成测试：

```bash
# 确保服务正在运行
python tests/test_api.py
```

## 📁 项目结构

```
indextts2-api/
├── app.py              # 主应用入口
├── start.sh           # 启动脚本
├── requirements.txt   # 依赖列表
├── config/
│   └── settings.py    # 配置文件
├── api/
│   ├── __init__.py
│   ├── models.py      # 数据模型
│   └── routes.py      # API路由
├── core/
│   ├── __init__.py
│   └── tts_service.py # 核心TTS服务
└── tests/
    └── test_api.py    # 集成测试
```

## 🔧 开发

### 添加新的API端点

1. 在 `api/models.py` 中定义数据模型
2. 在 `api/routes.py` 中添加路由处理函数
3. 在 `core/tts_service.py` 中实现业务逻辑

### 本地开发

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app:app --reload --host 0.0.0.0 --port 7861
```

## 📦 部署

### Docker 部署（可选）

```bash
# 构建镜像
docker build -t indextts2-api .

# 运行容器
docker run -p 7861:7861 -v $(pwd)/../checkpoints:/app/checkpoints indextts2-api
```

### 系统服务部署

```bash
# 作为系统服务运行
sudo cp indextts2-api.service /etc/systemd/system/
sudo systemctl enable indextts2-api
sudo systemctl start indextts2-api
```

## 🤝 集成示例

### Python 客户端

```python
import requests
import base64

# 语音合成
response = requests.post("http://localhost:7861/api/v1/tts", json={
    "text": "你好，世界！",
    "language": "zh"
})

if response.status_code == 200:
    data = response.json()
    audio_data = base64.b64decode(data["audio_data"])
    with open("output.wav", "wb") as f:
        f.write(audio_data)
```

### JavaScript 客户端

```javascript
// 语音合成
const response = await fetch('http://localhost:7861/api/v1/tts', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        text: '你好，世界！',
        language: 'zh'
    })
});

const data = await response.json();
const audioData = atob(data.audio_data);
```

## 🐛 故障排除

### 常见问题

1. **模型加载失败**
   - 检查 `../checkpoints` 目录是否存在
   - 确保所有模型文件都已下载

2. **端口被占用**
   - 修改 `INDEX_TTS_API_PORT` 环境变量
   - 或使用 `lsof -i :7861` 查看端口使用情况

3. **导入错误**
   - 确保在正确的目录中运行
   - 检查 Python 路径设置

### 日志查看

```bash
# 查看服务日志
tail -f logs/indextts2-api.log

# 查看系统日志
journalctl -u indextts2-api -f
```

## 📄 许可证

本项目基于 IndexTTS2 开源许可证。

## 🙋‍♂️ 支持

如有问题，请提交 Issue 或查看原项目文档。