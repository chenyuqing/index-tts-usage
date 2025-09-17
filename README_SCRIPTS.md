# IndexTTS2 启动脚本使用说明

## 脚本概述

为方便IndexTTS2的日常使用，提供了以下管理脚本：

| 脚本文件 | 功能描述 | 使用场景 |
|---------|---------|----------|
| `start.sh` | 前台启动服务 | 开发调试，可看到实时日志 |
| `start_background.sh` | 后台启动服务 | 生产使用，服务在后台运行 |
| `stop.sh` | 停止服务 | 安全停止IndexTTS2服务 |
| `status.sh` | 查看服务状态 | 检查服务运行状态和系统资源 |

## 使用方法

### 1. 前台启动（推荐用于测试）

```bash
./start.sh
```

**特点：**
- 实时显示日志输出
- 按 Ctrl+C 可直接停止
- 适合开发和调试

### 2. 后台启动（推荐用于生产）

```bash
./start_background.sh
```

**特点：**
- 服务在后台运行
- 自动检查端口占用
- 生成日志文件
- 创建PID文件便于管理

### 3. 停止服务

```bash
./stop.sh
```

**功能：**
- 温和终止进程（SIGTERM）
- 超时后强制终止（SIGKILL）
- 自动清理PID文件

### 4. 查看状态

```bash
./status.sh
```

**检查内容：**
- 进程运行状态
- 端口监听状态
- Web服务响应
- GPU加速状态
- 内存使用情况
- 最近日志输出

## 服务管理

### 完整启动流程

```bash
# 1. 启动后台服务
./start_background.sh

# 2. 检查状态
./status.sh

# 3. 访问Web界面
open http://127.0.0.1:7860
```

### 日常维护

```bash
# 查看实时日志
tail -f logs/indextts.log

# 重启服务
./stop.sh && ./start_background.sh

# 检查系统资源
./status.sh
```

## 目录结构

脚本运行后会创建以下目录结构：

```
index-tts/
├── start.sh                 # 前台启动脚本
├── start_background.sh      # 后台启动脚本
├── stop.sh                  # 停止脚本
├── status.sh               # 状态检查脚本
├── logs/                   # 日志目录
│   ├── indextts.log        # 服务日志
│   └── indextts.pid        # 进程ID文件
└── outputs/                # 输出音频文件目录
```

## 注意事项

1. **权限要求**：脚本需要可执行权限
2. **端口冲突**：脚本会自动处理7860端口占用
3. **环境检查**：启动前会验证uv、模型文件等
4. **日志管理**：建议定期清理日志文件
5. **系统要求**：适用于Mac系统，使用MPS加速

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查看端口占用
   lsof -i :7860

   # 手动终止进程
   kill -9 <PID>
   ```

2. **模型文件缺失**
   ```bash
   # 重新下载模型
   modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
   ```

3. **GPU检测失败**
   ```bash
   # 检查GPU状态
   uv run tools/gpu_check.py
   ```

4. **服务无响应**
   ```bash
   # 查看详细状态
   ./status.sh

   # 查看错误日志
   tail -n 50 logs/indextts.log
   ```

## 性能优化建议

- **内存监控**：定期检查内存使用，必要时重启服务
- **日志轮转**：定期备份和清理日志文件
- **系统资源**：监控CPU和GPU使用率
- **网络检查**：确保防火墙不阻止7860端口

---

**使用愉快！如有问题请检查日志文件或运行status.sh查看详细状态。**