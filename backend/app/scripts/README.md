# 数据库初始化说明

## 🎯 概述

本项目使用PostgreSQL作为数据库，通过Docker Compose自动初始化数据库表结构。

## 🚀 快速开始

### 1. **首次启动（推荐）**
```bash
# 启动所有服务，自动初始化数据库
docker-compose -f ../docker-compose-base.yml up -d
```

### 2. **重新初始化数据库**
```bash
# 停止服务并删除数据卷
docker-compose -f ../docker-compose-base.yml down -v

# 重新启动，会重新运行初始化脚本
docker-compose -f ../docker-compose-base.yml up -d
```

## 📁 文件说明

### `init.sql`
- PostgreSQL初始化脚本
- 自动创建用户表结构
- 创建必要的索引
- 添加表和字段注释

### 自动执行时机
- 当PostgreSQL容器首次启动时
- 当数据卷为空时
- 挂载到`/docker-entrypoint-initdb.d/`目录

## 🔧 表结构

### users表
```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    extra_info TEXT
);
```

### 索引
- `idx_user_username`: 用户名唯一索引
- `idx_user_active_created`: 状态+创建时间复合索引

## ⚠️ 注意事项

1. **数据持久化**: 使用Docker数据卷，数据不会丢失
2. **初始化脚本**: 只在首次启动或数据卷为空时执行
3. **表结构修改**: 如需修改表结构，更新`init.sql`后重新初始化
4. **开发环境**: 可以随时使用`docker-compose down -v`清空数据

## 🛠️ 手动操作

### 连接到数据库
```bash
docker exec -it postgres psql -U app_user -d app_db
```

### 查看表结构
```sql
\dt
\d users
```

### 查看数据
```sql
SELECT * FROM users;
```

## 🔄 工作流程

1. **容器启动** → PostgreSQL服务启动
2. **检查数据卷** → 如果为空，执行init.sql
3. **创建表结构** → 自动创建users表
4. **应用启动** → 检查表结构是否正常
5. **服务就绪** → 可以开始使用

---

**优势**: 代码在任何新环境都能正常运行，无需手动操作数据库！
