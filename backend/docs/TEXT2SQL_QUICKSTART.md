# Text2SQL智能体快速开始指南

## 🚀 快速概览

Text2SQL智能体是一个将自然语言转换为SQL查询的工具，可作为研究者智能体的子工具使用。

**当前状态**: ✅ 基础MVP已完成（70%），可立即使用

---

## ⚡ Docker快速启动（推荐，2分钟）

**你的项目使用Docker部署，这是最简单的方式：**

```bash
# 1. 激活环境
conda activate gsk-poc

# 2. 启动所有服务（一条命令搞定！）
docker-compose -f docker-compose-base.yml up -d

# 3. 等待30秒，让服务完全启动

# 4. 验证
curl http://localhost:8000/health
docker exec -it postgres psql -U research_readonly -d app_db -c "SELECT COUNT(*) FROM companies;"

# 5. 测试Text2SQL
python scripts/test_postgres_mcp_tools.py
```

**就这么简单！** PostgreSQL、MCP服务、研报数据全部自动配置好了。

**关键点（Docker环境）**:
- ✅ 独立数据库 `research_reports_db`（不与app_db混用）
- ✅ PostgreSQL host是 `postgres`（容器名，不是localhost）
- ✅ 初始化脚本自动执行（按顺序：创建DB → 创建表 → 插入数据）
- ✅ 只读用户自动创建

---

## 📦 已实现的组件

### MCP-Service侧（PostgreSQL工具服务器）

✅ **数据库连接管理**
- 异步连接池
- SQL安全验证（三层防护）
- 结构化错误处理

✅ **Schema图优化**
- NetworkX图结构
- 智能表选择
- 减少token使用

✅ **6个核心MCP工具**
1. `sql_db_list_tables` - 列出表
2. `sql_db_schema` - 获取表结构
3. `sql_db_query` - 执行查询
4. `sql_db_query_checker` - 验证SQL
5. `get_schema_graph` - 获取Schema图
6. `get_column_samples` - 获取列样本

✅ **演示数据库**
- 研报数据库（research_reports_db）
- 5张表（公司、分析师、研报等）
- 100+条样例数据

---

## 🏗️ 环境搭建

### 1. 安装依赖

```bash
# MCP-Service侧
cd mcp-app
pip install -r requirements.txt
```

**新增依赖**:
- `asyncpg>=0.29.0` - PostgreSQL驱动
- `sqlparse>=0.4.4` - SQL解析
- `networkx>=3.1` - 图结构

### 2. 创建数据库

```bash
# 创建数据库和表结构
psql -U postgres -f scripts/setup_research_reports_db.sql

# 生成样例数据（100+条）
python scripts/generate_research_data.py
```

### 3. 配置环境变量

复制并修改配置文件：

```bash
cp config_example.env .env
```

关键配置：

```bash
# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=research_readonly
POSTGRES_PASSWORD=readonly_password_2024
POSTGRES_DB=research_reports_db
```

### 4. 启动MCP服务

```bash
cd mcp-app
python -m app.main
```

服务将在 `http://localhost:8000` 启动。

---

## 🧪 测试PostgreSQL工具

### 测试1：获取服务器列表

```bash
curl http://localhost:8000/api/v1/servers/
```

应该看到`postgres-server`在列表中。

### 测试2：获取PostgreSQL工具列表

```bash
curl http://localhost:8000/api/v1/servers/postgres-server/tools
```

应该看到6个工具。

### 测试3：列出数据库表

```bash
curl -X POST http://localhost:8000/api/v1/servers/postgres-server/tools/sql_db_list_tables/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {}}'
```

应该返回5张表的信息。

### 测试4：获取表结构

```bash
curl -X POST http://localhost:8000/api/v1/servers/postgres-server/tools/sql_db_schema/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"table_names": ["companies"]}}'
```

应该返回companies表的DDL和样本数据。

### 测试5：执行SQL查询

```bash
curl -X POST http://localhost:8000/api/v1/servers/postgres-server/tools/sql_db_query/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "SELECT name, industry, market_cap FROM companies LIMIT 5"}}'
```

应该返回5家公司的信息。

### 测试6：测试安全验证

```bash
# 尝试危险SQL（应该被拒绝）
curl -X POST http://localhost:8000/api/v1/servers/postgres-server/tools/sql_db_query/call \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"query": "DELETE FROM companies"}}'
```

应该返回错误：`禁止使用DELETE语句，只允许SELECT查询`

---

## 📊 数据库Schema概览

### companies（公司表）
```sql
SELECT code, name, industry, market_cap FROM companies LIMIT 3;

-- 结果：
-- 00700.HK | 腾讯控股有限公司 | 互联网 | 35000.50
-- BABA     | 阿里巴巴集团   | 电子商务 | 28000.00
-- PDD      | 拼多多         | 电子商务 | 15000.00
```

### analysts（分析师表）
```sql
SELECT name, institution, specialty FROM analysts LIMIT 3;

-- 结果：
-- 张明 | 中金公司 | 互联网
-- 李华 | 中金公司 | 消费电子
-- 王芳 | 中金公司 | 新能源汽车
```

### research_reports（研报表）
```sql
SELECT title, rating, publish_date FROM research_reports LIMIT 2;

-- 结果：
-- 腾讯控股：云业务持续高增长，维持买入评级 | 买入 | 2024-01-15
-- 阿里巴巴：电商基本盘稳固，云计算盈利改善 | 买入 | 2024-01-20
```

---

## 🔍 示例查询场景

数据库支持以下查询场景：

### 1. 简单过滤
```sql
SELECT * FROM companies WHERE industry = '互联网';
```

### 2. 聚合查询
```sql
SELECT rating, COUNT(*) as count 
FROM research_reports 
GROUP BY rating;
```

### 3. 多表JOIN
```sql
SELECT c.name, r.title, r.rating 
FROM companies c
JOIN research_reports r ON c.id = r.company_id
WHERE c.industry = '新能源汽车';
```

### 4. 时间过滤
```sql
SELECT * FROM research_reports 
WHERE publish_date >= '2024-01-01' 
  AND publish_date < '2024-02-01';
```

### 5. 复杂聚合
```sql
SELECT 
  a.name as analyst,
  a.institution,
  COUNT(r.id) as report_count
FROM analysts a
LEFT JOIN research_reports r ON a.id = r.analyst_id
GROUP BY a.id, a.name, a.institution
ORDER BY report_count DESC
LIMIT 5;
```

---

## 🎯 下一步

### 待实现（App侧）

1. **MCP客户端封装**
   - 封装HTTP调用
   - 错误处理

2. **Text2SQL LangGraph**
   - 状态定义
   - 9个节点实现
   - 条件路由

3. **优化组件**
   - 动态Prompt生成
   - Few-shot管理器
   - SQL缓存
   - 专有名词检索

4. **集成**
   - 注册为研究者工具
   - 配置管理

### 简化实施路径

如果时间紧张，可以：

1. **跳过优化组件**（缓存、Few-shot等）
2. **实现基础LangGraph**（3个核心节点）
   - `select_tables` - 选择表
   - `generate_sql` - 生成SQL
   - `execute` - 执行查询
3. **最小化集成**
   - 创建简单的`@tool`
   - 调用MCP工具
   - 返回结果

---

## 📚 文件结构

```
AI/
├── mcp-app/              # MCP服务（已实现）
│   └── app/
│       ├── core/
│       │   ├── db_manager.py      ✅ 数据库管理
│       │   └── schema_graph.py    ✅ Schema图
│       └── services/
│           └── postgres_server.py ✅ PostgreSQL服务器
│
├── app/                  # 主应用（待实现）
│   └── services/
│       ├── database/
│       │   └── mcp_postgres_client.py  ❌ MCP客户端
│       └── agent_orchestration/
│           ├── text2sql_state.py       ❌ 状态定义
│           ├── text2sql_nodes.py       ❌ 节点实现
│           ├── text2sql_graph.py       ❌ 图定义
│           └── text2sql_tool.py        ❌ 工具包装
│
├── scripts/              # 脚本
│   ├── setup_research_reports_db.sql  ✅ 数据库Schema
│   └── generate_research_data.py      ✅ 数据生成
│
├── docs/                 # 文档
│   ├── TEXT2SQL_IMPLEMENTATION_STATUS.md  ✅ 实施状态
│   └── TEXT2SQL_QUICKSTART.md            ✅ 快速开始
│
└── config_example.env    ✅ 配置示例
```

---

## 🐛 故障排除

### 问题1：数据库连接失败

**错误**: `asyncpg.exceptions.InvalidCatalogNameError`

**解决**:
```bash
# 确认数据库已创建
psql -U postgres -c "\l" | grep research_reports_db

# 如果不存在，运行初始化脚本
psql -U postgres -f scripts/setup_research_reports_db.sql
```

### 问题2：只读用户权限问题

**错误**: `permission denied`

**解决**:
```sql
-- 检查用户权限
\c research_reports_db
\du research_readonly

-- 重新授权
GRANT SELECT ON ALL TABLES IN SCHEMA public TO research_readonly;
```

### 问题3：PostgreSQL服务器未注册

**现象**: 在服务器列表中看不到`postgres-server`

**解决**:
1. 检查环境变量是否正确设置
2. 查看MCP服务日志
3. 确认PostgreSQL可连接

---

## 💡 提示

1. **安全性**: 只读用户确保不会误删数据
2. **演示数据**: 覆盖多种查询场景，便于测试
3. **错误处理**: 详细的错误信息帮助调试
4. **Schema注释**: 所有表和列都有详细注释

---

## 📞 支持

遇到问题？查看：
1. [实施状态文档](TEXT2SQL_IMPLEMENTATION_STATUS.md)
2. [完整计划](../text2sql-agent-implementation.plan.md)
3. 代码注释

---

**最后更新**: 2025-10-11

