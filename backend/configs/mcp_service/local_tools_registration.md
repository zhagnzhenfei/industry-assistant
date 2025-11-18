# 本地开发工具集注册和使用说明

## 工具集概述

本地开发工具集为MCP服务提供了常用的开发工具功能，包括：

- **代码执行工具**: Python、Node.js、Shell代码的安全执行
- **文件操作工具**: 文件读写、搜索、目录管理等
- **Git操作工具**: 版本控制常用操作
- **数据库操作工具**: PostgreSQL、SQLite数据库操作
- **项目初始化工具**: 快速创建项目模板

## 工具注册方式

### 方法1：直接添加到tools.json

将 `local_dev_tools.json` 中的工具配置复制到 `configs/tools.json` 文件中。

### 方法2：动态加载本地工具配置

```python
import json

# 加载本地工具配置
with open('configs/local_dev_tools.json', 'r', encoding='utf-8') as f:
    local_tools = json.load(f)

# 添加到现有工具列表中（需要实现工具管理API调用）
for tool in local_tools:
    # 调用MCP服务的工具添加API
    # POST /api/v1/tools
    pass
```

## 工具功能详细说明

### 1. 代码执行工具

#### Python执行器 (`python_executor`)
```json
{
  "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)\nprint(f'fibonacci(10) = {fibonacci(10)}')",
  "include_output": true
}
```

#### Node.js执行器 (`nodejs_executor`)
```json
{
  "code": "const arr = [1, 2, 3, 4, 5];\nconst sum = arr.reduce((a, b) => a + b, 0);\nconsole.log('Sum:', sum);",
  "include_output": true
}
```

#### Shell执行器 (`shell_executor`)
```json
{
  "command": "ls -la | head -10",
  "include_output": true
}
```

### 2. 文件操作工具

#### 文件读取器 (`file_reader`)
```json
{
  "file_path": "app/main.py",
  "encoding": "utf-8"
}
```

#### 文件写入器 (`file_writer`)
```json
{
  "file_path": "test.txt",
  "content": "Hello, MCP!",
  "encoding": "utf-8",
  "create_dirs": true
}
```

#### 文件搜索器 (`file_search`)
```json
{
  "pattern": "TODO|FIXME",
  "search_path": ".",
  "recursive": true,
  "file_type": "code"
}
```

#### 目录列表器 (`directory_list`)
```json
{
  "dir_path": "./app",
  "include_hidden": false,
  "details": true
}
```

### 3. Git操作工具

#### Git状态检查器 (`git_status`)
```json
{
  "repo_path": "."
}
```

#### Git提交器 (`git_commit`)
```json
{
  "message": "Add new feature",
  "files": ["app.py", "config.py"],
  "repo_path": "."
}
```

#### Git分支管理器 (`git_branch_manager`)
```json
{
  "operation": "create",
  "branch_name": "feature/new-tool",
  "checkout": true,
  "repo_path": "."
}
```

#### Git同步器 (`git_push_pull`)
```json
{
  "operation": "push",
  "remote": "origin",
  "branch": "main",
  "repo_path": "."
}
```

### 4. 数据库操作工具

#### 数据库连接测试器 (`db_connection_test`)
```json
{
  "db_type": "sqlite",
  "connection_params": {
    "database": "test.db"
  }
}
```

#### 数据库查询执行器 (`db_query_executor`)
```json
{
  "db_type": "sqlite",
  "connection_params": {
    "database": "test.db"
  },
  "query": "SELECT * FROM users WHERE age > ?",
  "params": [18]
}
```

#### 数据库信息查看器 (`db_info_getter`)
```json
{
  "db_type": "postgresql",
  "connection_params": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "postgres",
    "password": "password"
  }
}
```

### 5. 项目初始化工具

#### 项目初始化器 (`project_initializer`)
```json
{
  "project_name": "my-new-project",
  "project_type": "python",
  "base_path": "./projects",
  "include_git": true,
  "include_readme": true
}
```

## 安全考虑

### 代码执行安全
- Python执行器禁用了危险模块（os, subprocess, eval等）
- Node.js执行器禁用了文件系统和进程操作
- Shell执行器限制了危险命令（rm -rf, sudo等）
- 所有执行器都有超时保护（默认30秒）

### 文件操作安全
- 限制文件访问范围在指定目录内
- 防止目录遍历攻击
- 系统目录删除保护
- 文件类型检测和过滤

### 数据库安全
- 连接参数验证
- SQL注入防护
- 数据库操作权限控制

## 使用示例

### 完整工作流程示例

```python
# 1. 初始化项目
project_result = initialize_project(
    project_name="data-analysis",
    project_type="python",
    include_git=True
)

# 2. 创建Python脚本
write_result = write_file_content(
    file_path="data-analysis/src/analyze.py",
    content="""
import json
from collections import Counter

def analyze_data(data):
    counter = Counter(data)
    return dict(counter.most_common())

# 示例数据
data = ['apple', 'banana', 'apple', 'orange', 'banana', 'apple']
result = analyze_data(data)
print(json.dumps(result, indent=2))
"""
)

# 3. 执行脚本
exec_result = execute_python_code(
    code="""
import sys
sys.path.append('data-analysis/src')
exec(open('data-analysis/src/analyze.py').read())
"""
)

# 4. 查看Git状态
git_status_result = get_git_status("data-analysis")

# 5. 提交更改
commit_result = commit_git_changes(
    message="Add data analysis script",
    repo_path="data-analysis"
)
```

## 扩展开发

### 添加新工具

1. 在相应的模块文件中添加新功能
2. 在 `__init__.py` 中导出函数
3. 在 `local_dev_tools.json` 中添加工具配置
4. 注册到MCP服务的tools.json中

### 自定义工具类型

支持的工具类型：
- `function`: 本地Python函数调用
- `http`: HTTP服务调用
- `stdio`: 标准输入输出进程
- `websocket`: WebSocket服务
- `custom`: 自定义类型

## 故障排除

### 常见问题

1. **权限问题**: 确保有足够的文件系统权限
2. **路径问题**: 使用相对路径或确保绝对路径存在
3. **编码问题**: 默认使用UTF-8编码，必要时指定其他编码
4. **超时问题**: 长运行任务可以调整超时参数
5. **依赖问题**: 确保系统安装了必要的运行时（Python、Node.js、Git等）

### 调试建议

1. 查看工具返回的详细错误信息
2. 检查输入参数格式和类型
3. 验证文件路径和权限
4. 使用测试模式验证工具功能
5. 查看MCP服务日志获取更多信息

## 性能优化

### 代码执行优化
- 合理使用超时设置
- 避免无限循环
- 优化算法复杂度

### 文件操作优化
- 大文件使用流式处理
- 批量操作减少IO次数
- 合理使用缓存

### 数据库操作优化
- 使用索引优化查询
- 批量操作减少连接次数
- 合理设置查询结果限制

这个本地开发工具集为开发者提供了强大的辅助功能，可以显著提高开发效率和代码质量。通过MCP服务的统一接口，可以方便地在各种应用场景中集成和使用这些工具。`