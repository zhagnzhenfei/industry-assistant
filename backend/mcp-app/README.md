# Generic MCP Service

一个专注于工具管理的通用MCP（Model Context Protocol）服务。

## 🎯 项目特点

- **轻量级设计**: 专注于核心的工具管理功能，无复杂的业务逻辑
- **配置驱动**: 通过JSON配置文件动态管理工具
- **多工具类型支持**: 支持函数、HTTP、STDIO、WebSocket等多种工具类型
- **RESTful API**: 提供完整的工具管理API接口
- **易于集成**: 上层应用可以轻松集成和扩展

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保Python 3.8+
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

```bash
# 复制环境变量文件
cp env.example .env

# 根据需要修改.env文件
```

### 4. 启动服务

```bash
# 直接启动
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问服务

- 服务地址: http://localhost:8000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📁 项目结构

```
python-mcp-app/
├── app/
│   ├── main.py                 # 应用入口
│   ├── core/
│   │   └── config.py          # 配置管理
│   ├── models/
│   │   └── tool_models.py     # 工具数据模型
│   ├── services/
│   │   ├── tool_manager.py    # 工具管理器
│   │   └── execution_service.py # 工具执行服务
│   └── api/
│       ├── tools.py           # 工具管理API
│       └── execution.py       # 工具执行API
├── configs/
│   └── tools.json             # 工具配置文件
├── requirements.txt            # Python依赖
└── README.md                  # 项目说明
```

## 🔧 核心功能

### 工具管理

- **添加工具**: 通过API或配置文件添加新工具
- **删除工具**: 移除不需要的工具
- **更新工具**: 修改工具配置和属性
- **启用/禁用**: 控制工具的使用状态
- **工具搜索**: 按分类、标签、关键词搜索工具

### 工具执行

- **单工具执行**: 执行单个工具
- **批量执行**: 同时执行多个工具
- **执行监控**: 查看活跃的执行任务
- **执行取消**: 取消正在执行的工具
- **工具测试**: 测试工具配置是否正确

### 工具类型支持

- **Function**: 函数调用类型
- **HTTP**: HTTP服务类型
- **STDIO**: 标准输入输出类型
- **WebSocket**: WebSocket服务类型
- **Custom**: 自定义类型

## 📖 API接口

### 工具管理接口

- `GET /api/v1/tools` - 获取工具列表
- `POST /api/v1/tools` - 添加新工具
- `GET /api/v1/tools/{tool_id}` - 获取特定工具
- `PUT /api/v1/tools/{tool_id}` - 更新工具
- `DELETE /api/v1/tools/{tool_id}` - 删除工具
- `POST /api/v1/tools/{tool_id}/enable` - 启用工具
- `POST /api/v1/tools/{tool_id}/disable` - 禁用工具

### 工具执行接口

- `POST /api/v1/execution/execute` - 执行工具
- `POST /api/v1/execution/execute/batch` - 批量执行工具
- `POST /api/v1/execution/cancel/{request_id}` - 取消执行
- `GET /api/v1/execution/active` - 获取活跃执行任务
- `POST /api/v1/execution/test/{tool_id}` - 测试工具

### 系统接口

- `GET /` - 服务信息
- `GET /health` - 健康检查
- `GET /info` - 服务详细信息

## ⚙️ 配置说明

### 工具配置文件 (configs/tools.json)

```json
{
  "tools": [
    {
      "id": "tool_id",
      "name": "工具名称",
      "description": "工具描述",
      "version": "1.0.0",
      "type": "http",
      "config": {
        "url": "https://api.example.com",
        "method": "GET"
      },
      "input_schema": {
        "type": "object",
        "properties": {
          "param": {"type": "string"}
        },
        "required": ["param"]
      },
      "tags": ["tag1", "tag2"],
      "category": "category",
      "status": "active"
    }
  ]
}
```

### 环境变量配置

```bash
# 应用配置
APP_NAME=Generic MCP Service
APP_VERSION=1.0.0
DEBUG=true

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 日志配置
LOG_LEVEL=INFO
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

## 🔍 使用示例

### 1. 添加工具

```bash
curl -X POST "http://localhost:8000/api/v1/tools" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my_tool",
    "name": "My Tool",
    "description": "A custom tool",
    "type": "http",
    "config": {"url": "https://api.example.com"},
    "input_schema": {"type": "object", "properties": {}},
    "status": "active"
  }'
```

### 2. 执行工具

```bash
curl -X POST "http://localhost:8000/api/v1/execution/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "my_tool",
    "arguments": {"param": "value"}
  }'
```

### 3. 获取工具列表

```bash
curl "http://localhost:8000/api/v1/tools"
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your.email@example.com

---

**Generic MCP Service** - 让工具管理变得简单高效！
