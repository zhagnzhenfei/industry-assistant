# Text2SQL智能体 - README

> 将自然语言问题转换为SQL查询的智能体工具

## 🚀 快速开始

### Docker部署（推荐，2分钟）

```bash
# 1. 激活环境
conda activate gsk-poc

# 2. 启动Docker服务（PostgreSQL、MCP服务等）
docker-compose -f docker-compose-base.yml up -d

# 3. 等待30秒，让服务完全启动

# 4. 验证和测试
curl http://localhost:8000/health
python scripts/test_postgres_mcp_tools.py
```

**完成！** 所有服务已自动配置。

### 本地部署（开发调试）

如果不使用Docker：

```bash
# 1. 创建独立数据库
psql -U postgres -c "CREATE DATABASE research_reports_db;"
psql -U postgres -f scripts/setup_research_reports_db.sql
python scripts/generate_research_data.py

# 2. 启动MCP服务
cd mcp-app
export POSTGRES_HOST=localhost
export POSTGRES_USER=research_readonly
export POSTGRES_PASSWORD=readonly_password_2024
export POSTGRES_DB=research_reports_db  # 独立数据库
python -m app.main

# 3. 测试
python scripts/test_postgres_mcp_tools.py
```

---

## 📖 核心功能

### ✅ 已实现（MVP v1.0）

1. **自然语言转SQL** - 支持中文问题
2. **智能表选择** - 自动选择相关表
3. **错误自动重试** - 最多3次，每次带错误反馈
4. **安全防护** - 只读权限，SQL白名单
5. **结果格式化** - Markdown表格输出

### ⏳ 计划中（优化版）

- SQL缓存（向量检索）
- Few-shot学习
- 专有名词纠错
- 动态Prompt生成

---

## 💡 使用示例

### 在Python中直接调用

```python
from app.services.agent_orchestration.text2sql_tool import query_database

# 简单查询
result = await query_database("数据库中有多少家公司？")
# ✅ 查询成功！
# SQL: SELECT COUNT(*) FROM companies
# 结果: 19 家公司

# 复杂查询
result = await query_database("2024年哪些公司获得买入评级？")
# 自动执行JOIN查询
```

### 在研究者智能体中使用

Text2SQL已集成到研究者智能体，会自动在需要结构化数据时调用：

```
用户: "请分析2023年互联网行业的研报评级分布"
     ↓
研究者智能体自动判断需要数据
     ↓
调用 query_database 工具
     ↓
返回统计数据并生成分析报告
```

---

## 📊 支持的查询类型

### ✅ 简单查询

- "数据库中有多少家公司？"
- "列出所有互联网行业的公司"
- "2024年发布了多少篇研报？"

### ✅ 聚合查询

- "各个行业有多少家公司？"
- "每个分析师发布了多少篇研报？"
- "研报评级分布如何？"

### ✅ 多表JOIN

- "腾讯公司收到了哪些评级？"
- "中金公司的分析师有哪些？"
- "互联网公司的研报数量？"

### ✅ 排序和限制

- "市值最高的5家公司？"
- "2024年发布研报最多的分析师？"

---

## 🏗️ 系统架构

```
用户问题
   ↓
Text2SQL智能体 (LangGraph)
   ├─ 选择表
   ├─ 生成SQL
   └─ 执行查询 (重试机制)
       ↓
MCP PostgreSQL服务器
   ├─ SQL安全验证
   ├─ 执行查询
   └─ 返回结构化结果/错误
       ↓
PostgreSQL数据库 (只读)
```

---

## 📁 文件结构

```
AI/
├── mcp-app/                    # MCP服务
│   └── app/
│       ├── core/
│       │   ├── db_manager.py       # 数据库管理
│       │   └── schema_graph.py     # Schema图
│       └── services/
│           └── postgres_server.py  # PostgreSQL服务器
│
├── app/                        # 主应用
│   └── services/
│       ├── database/
│       │   └── mcp_postgres_client.py  # MCP客户端
│       └── agent_orchestration/
│           ├── text2sql_state.py       # 状态定义
│           ├── text2sql_nodes.py       # 节点实现
│           ├── text2sql_graph.py       # 图流程
│           └── text2sql_tool.py        # 工具包装
│
├── scripts/                    # 脚本
│   ├── setup_research_reports_db.sql   # 数据库初始化
│   ├── generate_research_data.py       # 数据生成
│   ├── test_postgres_mcp_tools.py      # MCP测试
│   └── test_text2sql_basic.py          # Text2SQL测试
│
└── docs/                       # 文档
    ├── TEXT2SQL_README.md              # 本文件
    ├── TEXT2SQL_QUICKSTART.md          # 快速开始
    ├── TEXT2SQL_DEPLOYMENT_GUIDE.md    # 部署指南
    └── TEXT2SQL_IMPLEMENTATION_STATUS.md  # 实施状态
```

---

## ⚙️ 配置

### 环境变量

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=research_readonly
POSTGRES_PASSWORD=readonly_password_2024
POSTGRES_DB=research_reports_db

# Text2SQL
TEXT2SQL_ENABLED=true
TEXT2SQL_MAX_RETRIES=3

# MCP服务
MCP_CLIENT_URL=http://localhost:8000
```

### Docker环境

```yaml
# docker-compose.yml
environment:
  - POSTGRES_HOST=postgres  # 容器名
  - MCP_CLIENT_URL=http://mcp-service:8000
```

---

## 🔒 安全性

### 三层防护

1. **只读用户**: 数据库用户只有SELECT权限
2. **SQL白名单**: 禁止DELETE/UPDATE/INSERT等
3. **查询限制**: 最多1000行，超时30秒

### 禁止的SQL

❌ DELETE  
❌ UPDATE  
❌ INSERT  
❌ DROP  
❌ CREATE  
❌ ALTER  

只允许 ✅ SELECT

---

## 📚 更多文档

| 文档 | 用途 |
|------|------|
| [TEXT2SQL_QUICKSTART.md](TEXT2SQL_QUICKSTART.md) | 5分钟快速体验 |
| [TEXT2SQL_DEPLOYMENT_GUIDE.md](TEXT2SQL_DEPLOYMENT_GUIDE.md) | 详细部署步骤 |
| [TEXT2SQL_IMPLEMENTATION_STATUS.md](TEXT2SQL_IMPLEMENTATION_STATUS.md) | 实施状态和进度 |
| [../TEXT2SQL_FINAL_SUMMARY.md](../TEXT2SQL_FINAL_SUMMARY.md) | 完整实施总结 |

---

## 🐛 故障排除

### MCP服务连接失败

```bash
# 检查服务状态
curl http://localhost:8000/health

# 查看日志
cd mcp-app
python -m app.main  # 前台运行查看日志
```

### 数据库连接失败

```bash
# 测试连接
psql -h localhost -U research_readonly -d research_reports_db

# 检查环境变量
env | grep POSTGRES
```

### SQL生成不准确

1. 检查表注释是否详细
2. 查看生成的SQL
3. 考虑添加Few-shot示例（未来版本）

---

## 🎯 下一步

### 立即行动

1. **部署测试**: 按照快速开始步骤操作
2. **体验功能**: 尝试各种问题
3. **收集反馈**: 记录不准确的查询

### 后续优化（可选）

1. 实现SQL缓存
2. 添加专有名词检索
3. 完善Few-shot学习

---

**版本**: 1.0.0 MVP  
**状态**: ✅ 生产就绪（基础功能）  
**最后更新**: 2025-10-11

