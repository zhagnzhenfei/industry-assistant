# Standard MCP Gateway

基于标准MCP协议的轻量级网关服务

## 🎯 项目概述

这是一个符合Model Context Protocol标准的轻量级网关服务，提供统一的MCP服务器连接管理和工具调用接口。

## 🏗️ 架构特点

- **标准MCP协议**: 完全基于MCP JSON-RPC 2.0协议实现
- **轻量级设计**: 客户端直接连接MCP服务器，无中间层
- **多连接类型**: 支持SSE、STDIO、WebSocket等连接方式
- **动态发现**: 通过MCP协议自动发现工具、资源和提示
- **简洁API**: RESTful接口设计，易于集成

## 📁 项目结构

```
mcp-app/
├── app/
│   ├── api/
│   │   └── connections.py      # 统一连接管理API
│   ├── core/
│   │   └── config.py           # 应用配置管理
│   ├── models/
│   │   └── mcp_models.py       # 标准MCP协议模型
│   ├── services/
│   │   ├── mcp_client.py       # MCP客户端
│   │   ├── mcp_connection_manager.py  # 连接管理器
│   │   ├── config_manager.py   # 配置管理器
│   │   └── postgres_server.py  # PostgreSQL服务器实现
│   └── main.py                 # 应用入口
├── configs/
│   └── mcp_servers.json        # MCP服务器配置
├── backup/                     # 旧代码备份
├── requirements.txt            # Python依赖
└── README.md                   # 项目文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置服务器

编辑 `configs/mcp_servers.json` 文件：

```json
{
  "servers": {
    "postgres-server": {
      "id": "postgres-server",
      "name": "PostgreSQL数据库服务器",
      "type": "stdio",
      "command": "python",
      "args": ["-m", "app.services.postgres_server"],
      "is_active": true
    }
  }
}
```

### 3. 启动服务

```bash
python app/main.py
```

服务将在 `http://localhost:8000` 启动

## 📖 API文档

### 连接管理

- `GET /api/v1/connections` - 获取连接列表
- `POST /api/v1/connections` - 添加新连接
- `GET /api/v1/connections/{id}` - 获取连接详情
- `DELETE /api/v1/connections/{id}` - 删除连接

### 连接操作

- `POST /api/v1/connections/{id}/connect` - 连接到服务器
- `POST /api/v1/connections/{id}/disconnect` - 断开连接

### 工具调用

- `GET /api/v1/connections/{id}/tools` - 获取工具列表
- `POST /api/v1/connections/{id}/tools/{name}/call` - 调用工具
- `GET /api/v1/connections/tools/all` - 获取所有可用工具

### 统计信息

- `GET /api/v1/connections/stats/summary` - 获取统计信息
- `GET /health` - 健康检查

## 🔧 配置说明

### 服务器配置

支持的连接类型：

- **stdio**: 标准输入输出连接
- **sse**: Server-Sent Events连接
- **websocket**: WebSocket连接

配置参数：

- `id`: 服务器唯一标识
- `name`: 服务器名称
- `type`: 连接类型
- `command`: 启动命令（stdio类型）
- `url`: 服务器URL（sse/websocket类型）
- `args`: 命令参数
- `env`: 环境变量
- `timeout`: 超时时间
- `is_active`: 是否激活

## 🐳 Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "app/main.py"]
```

## 📊 监控

### 健康检查

```bash
curl http://localhost:8000/health
```

### 服务状态

```bash
curl http://localhost:8000/api/v1/connections/stats/summary
```

## 🔍 故障排查

### 常见问题

1. **连接失败**
   - 检查服务器配置是否正确
   - 验证网络连接和端口可用性
   - 查看服务日志获取详细错误信息

2. **工具调用失败**
   - 确认服务器连接状态
   - 验证工具名称和参数格式
   - 检查服务器端工具实现

3. **配置加载失败**
   - 验证JSON配置文件格式
   - 检查文件权限
   - 使用配置导出接口验证

## 📚 开发指南

### 添加新的连接类型

1. 在 `mcp_models.py` 中添加新的 `ConnectionType`
2. 在 `mcp_connection_manager.py` 中实现连接类
3. 在连接管理器中注册新的连接类型

### 扩展API接口

在 `connections.py` 中添加新的端点，保持RESTful设计原则。

### 自定义服务器实现

参考 `postgres_server.py` 实现自定义的MCP服务器。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目采用MIT许可证。

## 🔗 相关资源

- [Model Context Protocol规范](https://modelcontextprotocol.io/)
- [MCP SDK文档](https://github.com/modelcontextprotocol/servers)