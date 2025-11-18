# 通用MCP服务快速启动指南

## 🚀 快速开始

### 1. 环境准备

确保你的系统已安装：
- Python 3.8+
- pip 包管理器

### 2. 克隆项目

```bash
git clone <your-repo-url>
cd python-mcp-app
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置环境

```bash
# 复制环境变量文件
cp env.example .env

# 根据需要修改.env文件（可选）
```

### 6. 启动服务

#### 方式1: 直接启动
```bash
python -m app.main
```

#### 方式2: 使用uvicorn
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式3: 使用启动脚本
```bash
# Linux/Mac
chmod +x scripts/start.sh
./scripts/start.sh

# Windows
scripts\start.bat
```

### 7. 验证服务

访问以下地址验证服务是否正常：

- **服务首页**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **API文档**: http://localhost:8000/docs
- **服务信息**: http://localhost:8000/info

## 🔧 核心功能测试

### 1. 查看工具列表

```bash
curl http://localhost:8000/api/v1/tools
```

### 2. 测试工具执行

```bash
# 测试HTTP工具
curl -X POST "http://localhost:8000/api/v1/execution/test/http_getter" \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "get", "params": {"test": "value"}}'
```

### 3. 运行完整测试

```bash
python test_generic_mcp.py
```

## 📁 项目结构

```
python-mcp-app/
├── app/                    # 应用主目录
│   ├── main.py            # 应用入口
│   ├── core/              # 核心模块
│   │   └── config.py      # 配置管理
│   ├── models/            # 数据模型
│   │   └── tool_models.py # 工具模型
│   ├── services/          # 业务服务
│   │   ├── tool_manager.py      # 工具管理器
│   │   └── execution_service.py # 执行服务
│   └── api/               # API接口
│       ├── tools.py       # 工具管理API
│       └── execution.py   # 执行API
├── configs/               # 配置文件
│   └── tools.json         # 工具配置
├── scripts/               # 脚本文件
│   └── start.sh          # 启动脚本
├── requirements.txt       # 依赖文件
├── test_generic_mcp.py   # 测试脚本
└── README.md             # 项目说明
```

## ⚙️ 配置说明

### 工具配置文件 (configs/tools.json)

工具配置文件定义了所有可用的工具：

```json
{
  "tools": [
    {
      "id": "tool_id",
      "name": "工具名称",
      "description": "工具描述",
      "type": "http",
      "config": {
        "url": "https://api.example.com",
        "method": "GET"
      },
      "input_schema": {
        "type": "object",
        "properties": {
          "param": {"type": "string"}
        }
      },
      "tags": ["tag1", "tag2"],
      "category": "category",
      "status": "active"
    }
  ]
}
```

### 支持的工具类型

- **function**: 函数调用类型
- **http**: HTTP服务类型
- **stdio**: 标准输入输出类型
- **websocket**: WebSocket服务类型
- **custom**: 自定义类型

## 🔍 常见问题

### 1. 端口被占用

如果8000端口被占用，可以修改端口：

```bash
# 修改.env文件
PORT=8001

# 或直接指定端口
uvicorn app.main:app --port 8001
```

### 2. 配置文件加载失败

确保配置文件存在且格式正确：

```bash
# 检查配置文件
ls -la configs/

# 验证JSON格式
python -m json.tool configs/tools.json
```

### 3. 依赖安装失败

```bash
# 升级pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

## 🐳 Docker部署

### 使用Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用Docker

```bash
# 构建镜像
docker build -t generic-mcp-service .

# 运行容器
docker run -d -p 8000:8000 generic-mcp-service
```

## 📚 下一步

1. **阅读API文档**: 访问 http://localhost:8000/docs 查看完整的API接口
2. **添加自定义工具**: 在 `configs/tools.json` 中添加新的工具定义
3. **集成到应用**: 使用API接口将MCP服务集成到你的应用中
4. **扩展功能**: 根据需要添加新的工具类型和执行逻辑

## 🤝 获取帮助

- 查看 [README.md](README.md) 了解项目详情
- 访问 [API文档](http://localhost:8000/docs) 查看接口说明
- 提交 [Issue](https://github.com/your-repo/issues) 报告问题
- 参与 [讨论](https://github.com/your-repo/discussions) 交流想法

---

**通用MCP服务** - 让工具管理变得简单高效！ 🚀
