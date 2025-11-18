# MCP本地开发工具集使用指南

## 📋 工具列表概览

基于服务信息统计，当前MCP服务已成功加载 **16个本地开发工具**，全部处于活跃状态。

### 🛠️ 可用工具分类

**代码执行工具 (3个)**
- ✅ `python_executor` - Python代码执行器
- ✅ `nodejs_executor` - Node.js代码执行器
- ✅ `shell_executor` - Shell命令执行器

**文件操作工具 (4个)**
- ✅ `file_reader` - 文件读取器
- ✅ `file_writer` - 文件写入器
- ✅ `file_search` - 文件搜索器
- ✅ `directory_list` - 目录列表器

**Git操作工具 (5个)**
- ✅ `git_status` - Git状态检查器
- ✅ `git_commit` - Git提交器
- ✅ `git_branch_manager` - Git分支管理器
- ✅ `git_push_pull` - Git同步器
- ✅ `git_history` - Git历史查看器

**数据库操作工具 (3个)**
- ✅ `db_connection_test` - 数据库连接测试器
- ✅ `db_query_executor` - 数据库查询执行器
- ✅ `db_info_getter` - 数据库信息查看器

**项目开发工具 (1个)**
- ✅ `project_initializer` - 项目初始化器

## 🔍 获取工具信息的方法

### 方法1: 通过服务信息端点
```bash
curl http://localhost:8000/info
```

返回的服务信息包含：
- `statistics.total_tools`: 工具总数
- `statistics.active_tools`: 活跃工具数
- `statistics.categories`: 工具分类统计
- `api_endpoints`: 可用的API端点

### 方法2: 通过健康检查端点
```bash
curl http://localhost:8000/health
```

返回健康状态包含：
- `tools_count`: 工具数量
- `active_tools`: 活跃工具数量

### 方法3: 通过OpenAPI文档
```bash
curl http://localhost:8000/openapi.json
```

查看完整的API文档和可用的端点。

## ⚡ 工具使用示例

### 1. Python代码执行
```python
import requests

tool_request = {
    "tool_id": "python_executor",
    "arguments": {
        "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f\"斐波那契数列第10项: {result}\")
"""
    },
    "request_id": "python-test-001"
}

response = requests.post(
    'http://mcp-service:8000/api/v1/execution/execute',
    json=tool_request
)
```

### 2. 文件内容读取
```python
tool_request = {
    "tool_id": "file_reader",
    "arguments": {
        "file_path": "/app/configs/tools.json",
        "encoding": "utf-8"
    }
}
```

### 3. Git仓库状态检查
```python
tool_request = {
    "tool_id": "git_status",
    "arguments": {
        "repo_path": "/app"
    }
}
```

### 4. 数据库连接测试
```python
tool_request = {
    "tool_id": "db_connection_test",
    "arguments": {
        "db_type": "sqlite",
        "connection_params": {
            "database": "/tmp/test.db"
        }
    }
}
```

## 🚀 快速测试所有工具

```python
import requests

# 测试所有工具的可用性
tools_to_test = [
    ("python_executor", {"code": "print('Hello Python!')"}),
    ("nodejs_executor", {"code": "console.log('Hello Node.js!');"}),
    ("shell_executor", {"command": "echo 'Hello Shell!'"}),
    ("file_reader", {"file_path": "/app/README.md"}),
    ("git_status", {"repo_path": "/app"}),
]

base_url = 'http://mcp-service:8000/api/v1/execution/execute'

for tool_id, args in tools_to_test:
    response = requests.post(base_url, json={
        "tool_id": tool_id,
        "arguments": args,
        "request_id": f"test-{tool_id}"
    })

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {tool_id}: {'成功' if result.get('success') else '失败'}")
    else:
        print(f"❌ {tool_id}: HTTP {response.status_code}")
```

## 📊 工具统计信息

**当前状态 (基于服务信息):**
- 🔧 总工具数: 16个
- ⚡ 活跃工具: 16个
- 📂 工具分类: development (16个)
- 🏷️ 工具标签: 暂无分类标签

## 🔧 注意事项

1. **安全限制**: 所有代码执行工具都有安全限制，禁用了危险操作
2. **超时设置**: 默认执行超时为30秒，可根据需要调整
3. **文件访问**: 文件操作工具限制在容器内部路径
4. **数据库支持**: 目前支持SQLite和PostgreSQL
5. **Git操作**: 需要目标路径是有效的Git仓库

## 🎯 使用建议

1. **开发辅助**: 使用代码执行工具快速测试算法和逻辑
2. **文件管理**: 利用文件操作工具进行配置文件处理
3. **版本控制**: 使用Git工具自动化版本管理流程
4. **数据处理**: 结合数据库工具进行数据操作和分析
5. **项目初始化**: 使用项目初始化器快速创建标准化项目结构

这套本地开发工具集为AI系统提供了强大的本地开发辅助能力，可以显著提高开发效率和代码质量！

---
*最后更新: 基于MCP服务实时状态生成*