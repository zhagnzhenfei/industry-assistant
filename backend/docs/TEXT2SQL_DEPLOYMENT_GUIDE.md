# Text2SQL智能体部署指南

## 📋 概述

本指南详细说明如何部署和使用Text2SQL智能体。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      App Container                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │        Text2SQL Agent (LangGraph)                     │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │select_tables│→ │generate_sql  │→ │execute_sql  │  │  │
│  │  └─────────────┘  └──────────────┘  └─────────────┘  │  │
│  │         ↑                                     │        │  │
│  │         └─────────────(失败重试)──────────────┘        │  │
│  └───────────────────────────────────────────────────────┘  │
│                         ↓ HTTP调用                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   MCP-Service Container                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           PostgreSQL MCP Server                       │  │
│  │  ┌──────────────────┐  ┌────────────────────────────┐ │  │
│  │  │  DatabaseManager │  │     SchemaGraph            │ │  │
│  │  │  - 连接池        │  │  - NetworkX图结构          │ │  │
│  │  │  - SQL验证       │  │  - 智能表选择              │ │  │
│  │  │  - 错误处理      │  │                            │ │  │
│  │  └──────────────────┘  └────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────┐ │
│  │  │  6个MCP工具                                        │ │
│  │  │  1. sql_db_list_tables                            │ │
│  │  │  2. sql_db_schema                                 │ │
│  │  │  3. sql_db_query                                  │ │
│  │  │  4. sql_db_query_checker                          │ │
│  │  │  5. get_schema_graph                              │ │
│  │  │  6. get_column_samples                            │ │
│  │  └────────────────────────────────────────────────────┘ │
│  └───────────────────────────────────────────────────────┘  │
│                         ↓ SQL查询                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                        │
│              research_reports_db (只读访问)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 部署步骤

```bash
docker-compose -f docker-compose-base.yml up -d --build mcp-service
```

### 第6步：测试PostgreSQL工具

```bash
# 运行MCP工具测试
python scripts/test_postgres_mcp_tools.py
```

预期输出：
```
✅ 服务健康
✅ PostgreSQL服务器已注册
✅ 找到6个工具
✅ 成功获取5张表
✅ Schema获取成功
...
```

### 第7步：启动主应用（App）

```bash

# 启动应用
python app/app_main.py
```

### 第8步：测试Text2SQL智能体

```bash
# 运行Text2SQL测试
python scripts/test_text2sql_basic.py
```

---

## 🧪 使用示例

### 在Python代码中使用

```python
from app.services.agent_orchestration.text2sql_tool import query_database

# 简单查询
result = await query_database("数据库中有多少家公司？")
print(result)

# 复杂查询
result = await query_database("2024年哪些公司获得买入评级最多？")
print(result)

# 聚合查询
result = await query_database("各个行业的公司数量分布？")
print(result)
```

### 在研究者智能体中使用

Text2SQL工具已经自动集成到研究者智能体的工具链中，当用户询问需要结构化数据的问题时，研究者会自动调用此工具。

```python
# 研究者会自动选择合适的工具
user_question = "请分析一下2023年科技行业的研报评级分布"

# 研究者可能会：
# 1. 使用query_database获取数据
# 2. 分析数据
# 3. 撰写分析报告
```

---

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `POSTGRES_HOST` | PostgreSQL主机 | localhost | postgres (Docker) |
| `POSTGRES_PORT` | PostgreSQL端口 | 5432 | 5432 |
| `POSTGRES_USER` | 数据库用户 | - | research_readonly |
| `POSTGRES_PASSWORD` | 数据库密码 | - | readonly_password_2024 |
| `POSTGRES_DB` | 数据库名 | - | research_reports_db |
| `TEXT2SQL_ENABLED` | 启用Text2SQL | true | true/false |
| `TEXT2SQL_MAX_RETRIES` | 最大重试次数 | 3 | 1-5 |
| `MCP_CLIENT_URL` | MCP服务URL | http://localhost:8000 | - |

### 数据库配置

**只读用户** (推荐用于生产环境)：
- 用户: `research_readonly`
- 权限: 仅SELECT
- 用途: 防止误操作

**开发调试** (可使用管理员用户):
- 用户: `postgres` 或其他管理员
- 用途: 调试、数据初始化

---

## 🔍 测试用例

### 基础查询测试

```python
# 测试1：计数查询
"数据库中有多少家公司？"
# 预期SQL: SELECT COUNT(*) FROM companies

# 测试2：过滤查询
"列出所有互联网行业的公司"
# 预期SQL: SELECT * FROM companies WHERE industry = '互联网'

# 测试3：时间过滤
"2024年发布了多少篇研报？"
# 预期SQL: SELECT COUNT(*) FROM research_reports 
#          WHERE publish_date >= '2024-01-01' 
#            AND publish_date < '2025-01-01'
```

### 复杂查询测试

```python
# 测试4：多表JOIN
"腾讯公司收到了哪些评级？"
# 预期SQL: SELECT r.rating, r.publish_date 
#          FROM companies c
#          JOIN research_reports r ON c.id = r.company_id
#          WHERE c.name LIKE '%腾讯%'

# 测试5：聚合分组
"每个行业有多少家公司？"
# 预期SQL: SELECT industry, COUNT(*) as count
#          FROM companies
#          GROUP BY industry

# 测试6：排序和限制
"市值最高的5家公司是哪些？"
# 预期SQL: SELECT name, market_cap FROM companies
#          ORDER BY market_cap DESC LIMIT 5
```

### 错误处理测试

```python
# 测试7：列名拼写错误（应自动重试）
question = "SELECT compny_name FROM companies"
# 第1次: 失败（column not found）
# 第2次: 应修正为 company_name

# 测试8：安全验证
question = "DELETE FROM companies"
# 预期: 被安全验证拒绝
```

---

## 🐛 故障排除

### 问题1：MCP服务连接失败

**症状**: `Connection refused` 或 `Service unavailable`

**解决方案**:
```bash
# 1. 检查MCP服务是否运行
curl http://localhost:8000/health

# 2. 查看MCP服务日志
cd mcp-app
python -m app.main

# 3. 检查端口占用
lsof -i :8000
```

### 问题2：PostgreSQL连接失败

**症状**: `Connection to database failed`

**解决方案**:
```bash
# 1. 检查PostgreSQL是否运行
pg_isready -h localhost -p 5432

# 2. 测试连接
psql -h localhost -U research_readonly -d research_reports_db

# 3. 检查环境变量
echo $POSTGRES_HOST
echo $POSTGRES_USER
echo $POSTGRES_DB
```

### 问题3：数据库不存在

**症状**: `database "research_reports_db" does not exist`

**解决方案**:
```bash
# 运行初始化脚本
psql -U postgres -f scripts/setup_research_reports_db.sql
```

### 问题4：工具未注册

**症状**: 服务器列表中没有`postgres-server`

**解决方案**:
1. 检查MCP服务启动日志
2. 确认环境变量正确
3. 查看错误日志: `mcp-app/logs/`

### 问题5：SQL执行超时

**症状**: `Query timeout`

**解决方案**:
1. 简化查询逻辑
2. 添加WHERE条件减少数据量
3. 检查是否缺少索引

---

## 📊 性能优化

### 数据库优化

```sql
-- 添加索引（如果查询慢）
CREATE INDEX idx_reports_date ON research_reports(publish_date);
CREATE INDEX idx_reports_company ON research_reports(company_id);
CREATE INDEX idx_companies_industry ON companies(industry);

-- 分析表（更新统计信息）
ANALYZE companies;
ANALYZE research_reports;
```

### 连接池配置

在环境变量中设置：
```bash
POSTGRES_MAX_CONNECTIONS=10  # 根据负载调整
```

---

## 🔒 安全最佳实践

### 1. 使用只读用户

**生产环境必须使用只读用户**:
```bash
POSTGRES_USER=research_readonly  # ✅ 推荐
# 不要使用 POSTGRES_USER=postgres  # ❌ 不安全
```

### 2. SQL白名单验证

系统自动拒绝：
- DELETE
- UPDATE
- INSERT
- DROP
- CREATE
- ALTER

### 3. 查询限制

- 最大结果: 1000行
- 超时时间: 30秒
- 自动添加LIMIT

### 4. 网络安全

在生产环境：
- MCP服务不应暴露到公网
- 使用内网或VPN访问
- 配置防火墙规则

---

## 📈 监控和日志

### 查看日志

```bash
# MCP服务日志
cd mcp-app
tail -f logs/mcp_service.log

# App日志
cd app
tail -f logs/app.log
```

### 监控指标

关键指标：
- SQL执行成功率
- 平均响应时间
- 错误类型分布
- 重试次数

可以在日志中查找：
```bash
grep "SQL执行成功" logs/*.log | wc -l
grep "SQL执行失败" logs/*.log | wc -l
```

---

## 🚀 Docker部署（推荐）

### Docker环境说明

你的项目使用Docker Compose部署，PostgreSQL已经在`docker-compose-base.yml`中配置。

### 步骤1：启动服务

```bash
# 使用docker-compose-base.yml启动所有服务
docker-compose -f docker-compose-base.yml up -d

# 如果mcp需要重新build
docker-compose -f docker-compose-base.yml up -d --build mcp-service
```

这会自动：
1. 启动PostgreSQL容器
2. 自动执行初始化脚本 (`setup_research_reports_db.sql`)
3. 创建表结构和初始数据
4. 创建只读用户 `research_readonly`
5. 启动MCP服务（已配置PostgreSQL连接）

### 步骤2：生成样例数据


**直接在postgres容器内执行**:
```bash
docker exec -it postgres psql -U app_user -d app_db -f /docker-entrypoint-initdb.d/02_create_research_db.sql
```

### 步骤3：验证部署

```bash
# 检查PostgreSQL容器
docker ps | grep postgres

# 检查MCP服务
curl http://localhost:8000/health

# 检查PostgreSQL服务器是否注册
curl http://localhost:8000/api/v1/servers | jq '.servers[] | select(.id=="postgres-server")'

# 测试数据库
docker exec -it postgres psql -U app_user -d app_db -c "\dt"

docker exec -it postgres psql -U research_readonly -d research_reports_db -c "\dt"
```

### Docker环境配置说明

在`docker-compose-base.yml`中，已自动配置：

```yaml
mcp-service:
  environment:
    # PostgreSQL连接（容器间网络）
    - POSTGRES_HOST=postgres        # ← 容器名
    - POSTGRES_PORT=5432
    - POSTGRES_USER=research_readonly
    - POSTGRES_PASSWORD=readonly_password_2024
    - POSTGRES_DB=research_reports_db            
  depends_on:
    postgres:
      condition: service_healthy    # ← 等待PostgreSQL就绪

postgres:
  volumes:
    # 自动执行初始化脚本
    - ./scripts/setup_research_reports_db.sql:/docker-entrypoint-initdb.d/02_research_db.sql:ro
```

### 重要提示（Docker环境）

1. **独立数据库**: 使用`research_reports_db`（与app_db分离，保持数据隔离）
2. **主机名**: `POSTGRES_HOST=postgres`（容器名），不是`localhost`
3. **自动初始化**: 
   - `00_create_research_db.sql` - 创建独立数据库
   - `setup_research_reports_db.sql` - 创建表和初始数据
4. **健康检查**: MCP服务会等待PostgreSQL就绪后再启动

**初始化脚本执行顺序**:
```
01_app_init.sql          → 创建app_db的表（你的业务数据）
02_create_research_db.sql → 创建research_reports_db数据库
03_research_tables.sql    → 在research_reports_db中创建表和数据
```

---

## 💡 最佳实践

### 1. 数据库设计

**必须遵守的规范**:
- ✅ 所有表都有COMMENT
- ✅ 所有列都有COMMENT（包含示例）
- ✅ 清晰的外键关系
- ✅ 适当的索引

**示例**:
```sql
COMMENT ON COLUMN companies.code IS 
    '股票代码。例如：00700.HK（腾讯）、BABA（阿里巴巴）';
```

### 2. 问题表述

**好的问题**（容易转换为SQL）:
- ✅ "2023年发布了多少篇研报？"
- ✅ "市值最高的5家公司是哪些？"
- ✅ "腾讯公司收到了哪些评级？"

**不好的问题**（难以处理）:
- ❌ "分析一下市场趋势"（太模糊）
- ❌ "帮我写份报告"（不是数据查询）

### 3. 错误处理

系统会自动重试（最多3次），每次重试都会：
- 包含上次的错误信息
- LLM尝试修正
- 记录所有尝试

---

## 📚 API参考

### query_database工具

```python
@tool
async def query_database(
    question: str,
    database: Optional[str] = None,
    config: RunnableConfig = None
) -> str:
    """
    查询结构化数据库
    
    Args:
        question: 自然语言问题
        database: 数据库名（可选）
        config: 运行时配置（可选）
    
    Returns:
        格式化的查询结果字符串
    """
```

**返回格式**:
```
✅ 查询成功！

**SQL语句**:
```sql
SELECT COUNT(*) FROM research_reports WHERE publish_date >= '2023-01-01'
```

**结果数量**: 1 行

**查询结果** (前10行):
| count |
| --- |
| 45 |
```

---

## 🎯 功能特性

### 当前版本（v1.0.0 简化版）

✅ **已实现**:
- SQL生成（使用qwen模型）
- 智能表选择（关键词匹配）
- SQL执行和结果返回
- 错误反馈和重试（最多3次）
- 安全验证（只读、白名单）
- 结果格式化

❌ **未实现**（计划中）:
- SQL缓存（向量检索）
- Few-shot学习
- 专有名词纠错
- 动态Prompt生成
- 完整9节点LangGraph

### 未来版本规划

**v1.1.0** (优化版):
- 添加SQL缓存
- 专有名词向量检索
- 性能提升50%

**v2.0.0** (完整版):
- Few-shot学习
- 动态Prompt生成
- 准确率达到80%+

---

## 📞 技术支持

### 查看日志

```bash
# MCP服务日志
tail -f mcp-app/logs/*.log

# 应用日志
tail -f app/logs/*.log
```

### 常见问题

1. **SQL生成不准确？**
   - 检查表注释是否详细
   - 查看生成的SQL和schema
   - 考虑添加Few-shot示例

2. **性能慢？**
   - 检查数据库索引
   - 查看SQL执行计划
   - 考虑添加缓存

3. **错误重试失败？**
   - 查看错误类型
   - 检查LLM是否理解错误信息
   - 可能需要调整Prompt

### 调试技巧

```python
# 1. 查看中间状态
from app.services.agent_orchestration.text2sql_tool import query_database_simple

result = await query_database_simple("你的问题")
print(result)  # 完整状态

# 2. 测试单个节点
from app.services.agent_orchestration.text2sql_nodes import select_tables_node

state = {"question": "测试问题"}
result = await select_tables_node(state)
print(result["selected_tables"])
```

---

## 📖 相关文档

- [实施状态文档](TEXT2SQL_IMPLEMENTATION_STATUS.md)
- [快速开始指南](TEXT2SQL_QUICKSTART.md)
- [完整计划](../text2sql-agent-implementation.plan.md)

---

**版本**: 1.0.0  
**最后更新**: 2025-10-11  
**状态**: 基础功能可用 ✅

