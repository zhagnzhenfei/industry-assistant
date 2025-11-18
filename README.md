# AI Industry Assistant

一个基于AI技术的行业助手应用，集成了文档管理、智能搜索、AI对话、用户记忆等功能的完整解决方案。

## 项目架构

本项目采用前后端分离的微服务架构：

- **前端**: React + TypeScript + Vite + Ant Design
- **后端**: FastAPI + PostgreSQL + Redis + Milvus
- **AI服务**: 集成OpenAI、DashScope等多种AI模型
- **MCP服务**: Model Context Protocol支持，提供工具管理和执行功能

## 快速开始

### 方法一：分别启动前后端

#### 后端启动

```bash
# 进入后端目录
cd backend

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 编辑docker-compose.yaml文件
# 修改nltk_data挂载目录
# 启动项目
docker compose up -d --build

```

#### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

```

## 环境配置

### 后端配置

复制并编辑环境变量文件：

```bash
cd backend
cp .env.example .env
```

关键配置项：

```env
# 数据库配置
DB_HOST=postgres
DB_USER=app_user
DB_PASSWORD=your_password_here

# AI服务配置
DASHSCOPE_API_KEY=your-dashscope-api-key
OPENAI_API_KEY=your-openai-api-key

# JWT配置
JWT_SECRET_KEY=your-jwt-secret-key
```

### 前端配置

前端配置主要在 `src/config` 目录下，包含API地址、环境配置等。

## 项目结构

```
industry_assistant/
├── frontend/                 # React前端应用
│   ├── src/
│   │   ├── components/      # 公共组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   └── utils/          # 工具函数
│   └── package.json
│
├── backend/                 # 后端服务
│   ├── app/                # 主应用
│   ├── mcp-app/           # MCP服务
│   ├── volumes/           # 数据卷
│   └── docker-compose.yml
│
└── README.md              # 项目说明文档
```

## 核心功能

### 前端功能
- 用户认证和权限管理
- 文档上传和管理
- 智能搜索和筛选
- AI对话界面
- 数据可视化
- 响应式设计

### 后端功能
- JWT认证系统
- 文档处理和解析（PDF、Word等）
- 向量数据库集成（Milvus）
- 智能语义搜索
- AI助手对话
- 用户记忆系统
- MCP协议支持

## 开发指南

### 添加新功能

1. **前端开发**：
   ```bash
   cd frontend
   npm run dev
   ```

2. **后端开发**：
   ```bash
   cd backend/app
   uvicorn app_main:app --reload
   ```

### 数据库操作

```bash
# 创建数据库表
python scripts/create_memory_tables.py --action create

# 检查表结构
python scripts/create_memory_tables.py --action check
```

### API测试

```bash
# 测试记忆API
curl http://localhost:8001/docs

# 运行测试脚本
python test_memory_integration.py
```

## 部署说明

### Docker部署

```bash
# 构建镜像
cd backend
docker-compose build

# 启动服务
docker-compose up -d
```

### 生产环境配置

1. 修改环境变量为生产配置
2. 配置HTTPS证书
3. 设置数据库备份策略
4. 配置监控和日志

## 故障排除

### 常见问题

1. **服务无法启动**
   - 检查端口占用：`netstat -tulpn | grep :8001`
   - 查看日志：`docker-compose logs -f app`

2. **数据库连接失败**
   - 检查PostgreSQL服务状态
   - 验证数据库连接配置

3. **前端页面无法访问**
   - 检查后端服务是否运行
   - 验证API地址配置

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f mcp-service
```

## 技术栈详情

### 前端技术栈
- **React 19** - 用户界面框架
- **TypeScript** - 类型安全的JavaScript
- **Vite** - 构建工具
- **Ant Design** - UI组件库
- **React Router** - 路由管理
- **Axios** - HTTP客户端

### 后端技术栈
- **FastAPI** - Web框架
- **PostgreSQL** - 关系型数据库
- **Redis** - 缓存数据库
- **Milvus** - 向量数据库
- **JWT** - 身份认证
- **OpenAI API** - AI服务
- **LangChain** - AI应用框架

## 开发团队

如有问题或建议，请提交Issue或联系开发团队。

## 许可证

MIT License