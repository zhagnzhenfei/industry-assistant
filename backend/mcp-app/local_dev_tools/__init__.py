"""
本地开发工具集
为MCP服务提供常用的开发工具功能
"""

from .executor import (
    execute_code,
    PythonExecutor,
    NodeJSExecutor,
    ShellExecutor
)

from .file_operations import (
    file_operation,
    FileOperations
)

from .git_operations import (
    git_operation,
    GitOperations
)

from .database_operations import (
    database_operation,
    DatabaseOperations
)

# 统一的工具接口映射
def execute_python_code(code: str, include_output: bool = True) -> Dict[str, Any]:
    """执行Python代码"""
    return execute_code('python', code, include_output=include_output)


def execute_nodejs_code(code: str, include_output: bool = True) -> Dict[str, Any]:
    """执行Node.js代码"""
    return execute_code('nodejs', code, include_output=include_output)


def execute_shell_command(command: str, include_output: bool = True) -> Dict[str, Any]:
    """执行Shell命令"""
    return execute_code('shell', command, include_output=include_output)


def read_file_content(file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
    """读取文件内容"""
    return file_operation('read', file_path=file_path, encoding=encoding)


def write_file_content(file_path: str, content: str, encoding: str = 'utf-8', create_dirs: bool = True) -> Dict[str, Any]:
    """写入文件内容"""
    return file_operation('write', file_path=file_path, content=content, encoding=encoding, create_dirs=create_dirs)


def search_files_and_content(pattern: str, search_path: str = ".", recursive: bool = True, file_type: str = "all") -> Dict[str, Any]:
    """搜索文件和内容"""
    return file_operation('search', pattern=pattern, search_path=search_path, recursive=recursive, file_type=file_type)


def list_directory_contents(dir_path: str = ".", include_hidden: bool = False, details: bool = True) -> Dict[str, Any]:
    """列出目录内容"""
    return file_operation('list', dir_path=dir_path, include_hidden=include_hidden, details=details)


def get_git_status(repo_path: str = ".") -> Dict[str, Any]:
    """获取Git状态"""
    return git_operation('status', repo_path=repo_path)


def commit_git_changes(message: str, files: list = None, repo_path: str = ".") -> Dict[str, Any]:
    """提交Git更改"""
    return git_operation('commit', message=message, files=files, repo_path=repo_path)


def manage_git_branches(operation: str, branch_name: str = None, checkout: bool = True, repo_path: str = ".") -> Dict[str, Any]:
    """管理Git分支"""
    return git_operation('create_branch' if operation == 'create' else 'switch_branch',
                        branch_name=branch_name, checkout=checkout, repo_path=repo_path)


def sync_git_changes(operation: str, remote: str = "origin", branch: str = None, repo_path: str = ".") -> Dict[str, Any]:
    """同步Git更改"""
    return git_operation(operation, remote=remote, branch=branch, repo_path=repo_path)


def get_git_history(max_count: int = 10, repo_path: str = ".") -> Dict[str, Any]:
    """获取Git历史"""
    return git_operation('commit_history', max_count=max_count, repo_path=repo_path)


def test_database_connection(db_type: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
    """测试数据库连接"""
    return database_operation('test_connection', db_type=db_type, connection_params=connection_params)


def execute_database_query(db_type: str, connection_params: Dict[str, Any], query: str, params: list = None) -> Dict[str, Any]:
    """执行数据库查询"""
    return database_operation('execute_query', db_type=db_type, connection_params=connection_params,
                            query=query, params=params)


def get_database_info(db_type: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
    """获取数据库信息"""
    return database_operation('get_info', db_type=db_type, connection_params=connection_params)


def initialize_project(project_name: str, project_type: str, base_path: str = ".", include_git: bool = True, include_readme: bool = True) -> Dict[str, Any]:
    """初始化项目"""
    try:
        project_path = Path(base_path) / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        # 创建项目结构
        if project_type == "python":
            # Python项目结构
            (project_path / "src").mkdir(exist_ok=True)
            (project_path / "tests").mkdir(exist_ok=True)
            (project_path / "docs").mkdir(exist_ok=True)

            # 创建基础文件
            init_content = f'"""{project_name} 包"""\n\n__version__ = "0.1.0"'
            write_file_content(str(project_path / "src" / "__init__.py"), init_content)

            requirements_content = f"""# {project_name} 依赖项
# 添加项目依赖包
"""
            write_file_content(str(project_path / "requirements.txt"), requirements_content)

        elif project_type == "nodejs":
            # Node.js项目结构
            (project_path / "src").mkdir(exist_ok=True)
            (project_path / "tests").mkdir(exist_ok=True)

            # 创建package.json
            package_content = json.dumps({
                "name": project_name,
                "version": "0.1.0",
                "description": f"{project_name} project",
                "main": "src/index.js",
                "scripts": {
                    "start": "node src/index.js",
                    "test": "echo \"Error: no test specified\" && exit 1"
                }
            }, indent=2)
            write_file_content(str(project_path / "package.json"), package_content)

            # 创建主文件
            main_content = f"// {project_name} 主文件\n\nconsole.log('{project_name} started!');"
            write_file_content(str(project_path / "src" / "index.js"), main_content)

        elif project_type == "web":
            # Web项目结构
            (project_path / "html").mkdir(exist_ok=True)
            (project_path / "css").mkdir(exist_ok=True)
            (project_path / "js").mkdir(exist_ok=True)
            (project_path / "images").mkdir(exist_ok=True)

            # 创建基础HTML
            html_content = f"""<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>{project_name}</title>\n    <link rel=\"stylesheet\" href=\"css/style.css\">\n</head>\n<body>\n    <h1>Welcome to {project_name}!</h1>\n    <script src=\"js/main.js\"></script>\n</body>\n</html>"""
            write_file_content(str(project_path / "html" / "index.html"), html_content)

            # 创建CSS
            css_content = f"/* {project_name} 样式文件 */\n\nbody {{\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n    background-color: #f5f5f5;\n}}\n\nh1 {{\n    color: #333;\n    text-align: center;\n}}"
            write_file_content(str(project_path / "css" / "style.css"), css_content)

            # 创建JavaScript
            js_content = f"// {project_name} JavaScript文件\n\nconsole.log('{project_name} loaded!');"
            write_file_content(str(project_path / "js" / "main.js"), js_content)

        elif project_type == "api":
            # API项目结构
            (project_path / "api").mkdir(exist_ok=True)
            (project_path / "models").mkdir(exist_ok=True)
            (project_path / "utils").mkdir(exist_ok=True)
            (project_path / "tests").mkdir(exist_ok=True)

            # 创建API主文件
            api_content = f"""# {project_name} API\n\nfrom flask import Flask, jsonify\n\napp = Flask(__name__)\n\n@app.route('/')\ndef hello():\n    return jsonify({{\n        \"message\": \"Welcome to {project_name}!\",\n        \"version\": \"0.1.0\"\n    }})\n\nif __name__ == '__main__':\n    app.run(debug=True)\n"""
            write_file_content(str(project_path / "api" / "app.py"), api_content)

            requirements_content = f"""# {project_name} API依赖项
flask>=2.0.0
"""
            write_file_content(str(project_path / "requirements.txt"), requirements_content)

        # 初始化Git仓库
        if include_git:
            try:
                subprocess.run(['git', 'init'], cwd=str(project_path), check=True, capture_output=True)
                gitignore_content = f"""# {project_name} Git忽略文件
# 依赖目录
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env

# IDE文件
.vscode/
.idea/
*.swp
*.swo

# 操作系统文件
.DS_Store
Thumbs.db

# 日志文件
*.log
logs/

# 临时文件
*.tmp
*.temp
"""
                write_file_content(str(project_path / ".gitignore"), gitignore_content)
            except Exception:
                pass  # Git初始化失败不影响项目创建

        # 创建README文件
        if include_readme:
            readme_content = f"""# {project_name}\n\n项目描述\n\n## 功能特性\n\n- 功能1\n- 功能2\n- 功能3\n\n## 安装和使用\n\n### 安装依赖\n\n```bash\n# 根据项目类型安装相应依赖\n```\n\n### 运行项目\n\n```bash\n# 根据项目类型运行相应命令\n```\n\n## 项目结构\n\n```\n{project_name}/\n├── ...\n```\n\n## 贡献指南\n\n欢迎提交Issue和Pull Request！\n\n## 许可证\n\nMIT License\n"""
            write_file_content(str(project_path / "README.md"), readme_content)

        return {
            "success": True,
            "message": f"项目 {project_name} 初始化成功",
            "project_path": str(project_path),
            "project_type": project_type,
            "include_git": include_git,
            "include_readme": include_readme
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"项目初始化失败: {str(e)}"
        }


__all__ = [
    'execute_python_code',
    'execute_nodejs_code',
    'execute_shell_command',
    'read_file_content',
    'write_file_content',
    'search_files_and_content',
    'list_directory_contents',
    'get_git_status',
    'commit_git_changes',
    'manage_git_branches',
    'sync_git_changes',
    'get_git_history',
    'test_database_connection',
    'execute_database_query',
    'get_database_info',
    'initialize_project',
    'CodeExecutor',
    'FileOperations',
    'GitOperations',
    'DatabaseOperations'
]