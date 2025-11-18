# AI应用后端服务

基于FastAPI构建的AI应用后端服务，集成了多种AI功能和用户记忆系统。

## 功能特性

### 核心功能
- **用户认证系统** - JWT认证，用户注册/登录
- **文档管理** - 支持多种格式文档的上传、解析和存储
- **智能搜索** - 基于向量数据库的语义搜索
- **AI助手** - 智能对话和问答系统
- **研究工具** - 深度研究和分析功能
- **图表生成** - 数据可视化功能
- **MCP集成** - Model Context Protocol支持

### 🆕 用户记忆功能 (mem0集成)
- **智能记忆存储** - 跨会话的用户偏好和上下文记忆
- **记忆分类管理** - 支持多种记忆类型（通用、偏好、上下文、事实、对话）
- **智能检索** - 基于查询的智能记忆搜索
- **上下文生成** - 为AI对话提供个性化上下文
- **重要性评分** - 1-10分的重要性评分系统
- **标签系统** - 支持记忆标签分类

## 技术栈

- **Web框架**: FastAPI 0.115.0
- **数据库**: PostgreSQL + Redis
- **向量数据库**: Milvus
- **AI/LLM**: OpenAI, LangChain, DashScope
- **文档解析**: python-docx, pdfplumber, pypdf
- **用户记忆**: mem0ai
- **认证**: JWT + bcrypt

## 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate gsk-poc

# 安装依赖
cd backend/app
pip install -r requirements.txt
```

### 2. 数据库设置

```bash
# 创建记忆功能数据库表
python scripts/create_memory_tables.py --action create

# 或者运行快速设置脚本
python scripts/setup_memory_feature.py
```

### 3. 配置环境变量

创建 `.env` 文件并配置必要的环境变量：

```env
# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379

# AI服务配置
OPENAI_API_KEY=your_openai_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

# 记忆功能配置
MEMORY_ENABLED=true
MEMORY_MAX_MEMORIES_PER_USER=1000
```

### 4. 启动服务

```bash
# 开发模式
python app_main.py

# 生产模式
gunicorn app_main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

### 5. 测试服务

```bash
# 测试记忆功能集成
python test_memory_integration.py

# 运行示例代码
python examples/memory_example.py
```

## API文档

启动服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### 记忆功能API

记忆相关接口位于 `/memory` 路径下：

- `POST /memory/create` - 创建记忆
- `GET /memory/{memory_id}` - 获取记忆
- `PUT /memory/{memory_id}` - 更新记忆
- `DELETE /memory/{memory_id}` - 删除记忆
- `POST /memory/search` - 搜索记忆
- `GET /memory/list` - 获取记忆列表
- `GET /memory/stats` - 获取记忆统计
- `GET /memory/context` - 获取用户上下文
- `POST /memory/conversation` - 添加对话记忆

## 项目结构

```
backend/app/
├── app_main.py              # 主应用入口
├── requirements.txt         # 依赖列表
├── models/                  # 数据模型
│   ├── user_models.py      # 用户模型
│   └── memory_models.py    # 记忆模型
├── schemas/                 # Pydantic模型
│   ├── user.py             # 用户相关
│   └── memory.py           # 记忆相关
├── service/                 # 业务逻辑
│   ├── auth_service.py     # 认证服务
│   └── memory_service.py   # 记忆服务
├── router/                  # API路由
│   ├── user_router.py      # 用户路由
│   └── memory_router.py    # 记忆路由
├── configs/                 # 配置文件
│   └── memory_config.py    # 记忆配置
├── scripts/                 # 脚本工具
│   ├── create_memory_tables.py
│   └── setup_memory_feature.py
├── examples/                # 示例代码
│   └── memory_example.py
├── docs/                    # 文档
│   └── MEMORY_FEATURE.md
└── test_memory_integration.py
```

## 记忆功能使用示例

### 创建记忆

```python
from service.memory_service import MemoryService
from schemas.memory import MemoryCreate

memory_service = MemoryService()

# 创建偏好记忆
memory_data = MemoryCreate(
    content="我喜欢使用Python进行开发",
    memory_type="preference",
    importance=8,
    tags=["programming", "python"]
)

result = memory_service.create_memory(user_id, memory_data)
```

### 搜索记忆

```python
from schemas.memory import MemorySearchRequest

search_request = MemorySearchRequest(
    query="python programming",
    memory_type="preference",
    limit=10
)

memories, total = memory_service.search_memories(user_id, search_request)
```

### 获取用户上下文

```python
# 获取用户上下文（用于AI对话）
context = memory_service.get_user_context(user_id, limit=20)
```

## 开发指南

### 添加新的记忆类型

1. 在 `configs/memory_config.py` 中添加新类型定义
2. 更新 `schemas/memory.py` 中的验证器
3. 在 `service/memory_service.py` 中添加相关逻辑

### 自定义记忆搜索

1. 扩展 `MemorySearchRequest` 模型
2. 在 `MemoryService.search_memories` 中实现新逻辑
3. 更新API接口

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t ai-app-backend .

# 运行容器
docker run -p 8001:8001 ai-app-backend
```

### 生产环境配置

1. 设置环境变量
2. 配置数据库连接
3. 设置Redis缓存
4. 配置日志系统
5. 设置监控和告警

## 监控和维护

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看记忆相关日志
grep "memory" logs/app.log
```

### 数据库维护

```bash
# 检查表结构
python scripts/create_memory_tables.py --action check

# 清理过期记忆（需要实现）
python scripts/cleanup_old_memories.py
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证连接字符串配置

2. **记忆功能不工作**
   - 检查数据库表是否创建
   - 验证环境变量配置

3. **API认证失败**
   - 检查JWT密钥配置
   - 验证用户令牌

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

MIT License

## 联系方式

如有问题，请提交Issue或联系开发团队。
