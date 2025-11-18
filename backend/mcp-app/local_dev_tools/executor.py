"""
本地代码执行工具集
提供Python、Node.js、Shell代码的安全执行环境
"""

import subprocess
import tempfile
import os
import json
import ast
from typing import Dict, Any, Optional
from datetime import datetime


class CodeExecutor:
    """代码执行器基类"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.execution_history = []

    def execute(self, code: str, **kwargs) -> Dict[str, Any]:
        """执行代码并返回结果"""
        raise NotImplementedError

    def validate_code(self, code: str) -> bool:
        """验证代码安全性"""
        raise NotImplementedError


class PythonExecutor(CodeExecutor):
    """Python代码执行器"""

    def validate_code(self, code: str) -> bool:
        """验证Python代码安全性"""
        try:
            # 基础语法检查
            ast.parse(code)

            # 危险模块检查
            dangerous_imports = ['os', 'subprocess', 'sys', '__import__', 'eval', 'exec']
            for dangerous in dangerous_imports:
                if dangerous in code:
                    return False

            return True
        except SyntaxError:
            return False

    def execute(self, code: str, include_output: bool = True) -> Dict[str, Any]:
        """安全执行Python代码"""
        start_time = datetime.now()

        if not self.validate_code(code):
            return {
                "success": False,
                "error": "代码包含危险操作或语法错误",
                "output": "",
                "execution_time": 0
            }

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # 执行代码
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            output = result.stdout if include_output else ""
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.returncode != 0 else "",
                "execution_time": execution_time,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"代码执行超时 (>{self.timeout}秒)",
                "output": "",
                "execution_time": self.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "execution_time": 0
            }
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class NodeJSExecutor(CodeExecutor):
    """Node.js代码执行器"""

    def validate_code(self, code: str) -> bool:
        """验证Node.js代码安全性"""
        dangerous_patterns = [
            'require(\"fs\")', 'require(\"child_process\")',
            'eval(', 'process.exit', '__dirname', '__filename'
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                return False

        return True

    def execute(self, code: str, include_output: bool = True) -> Dict[str, Any]:
        """执行Node.js代码"""
        start_time = datetime.now()

        if not self.validate_code(code):
            return {
                "success": False,
                "error": "代码包含危险操作",
                "output": "",
                "execution_time": 0
            }

        try:
            # 包装代码以捕获输出
            wrapped_code = f"""
            try {{
                {code}
            }} catch(error) {{
                console.error('执行错误:', error.message);
                process.exit(1);
            }}
            """

            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(wrapped_code)
                temp_file = f.name

            # 执行代码
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            output = result.stdout if include_output else ""
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.returncode != 0 else "",
                "execution_time": execution_time,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"代码执行超时 (>{self.timeout}秒)",
                "output": "",
                "execution_time": self.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "execution_time": 0
            }
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class ShellExecutor(CodeExecutor):
    """Shell命令执行器"""

    def validate_code(self, code: str) -> bool:
        """验证Shell命令安全性"""
        dangerous_commands = [
            'rm -rf', 'sudo', 'dd', 'mkfs', 'fdisk', '>', '>>',
            'wget', 'curl', 'nc', 'netcat'
        ]

        code_lower = code.lower()
        for dangerous in dangerous_commands:
            if dangerous in code_lower:
                return False

        return True

    def execute(self, code: str, include_output: bool = True) -> Dict[str, Any]:
        """执行Shell命令"""
        start_time = datetime.now()

        if not self.validate_code(code):
            return {
                "success": False,
                "error": "命令包含危险操作",
                "output": "",
                "execution_time": 0
            }

        try:
            # 执行命令
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=os.getcwd()
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            output = result.stdout if include_output else ""
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"

            return {
                "success": result.returncode == 0,
                "output": output,
                "error": result.stderr if result.returncode != 0 else "",
                "execution_time": execution_time,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"命令执行超时 (>{self.timeout}秒)",
                "output": "",
                "execution_time": self.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "execution_time": 0
            }


# 统一的执行器接口
def execute_code(language: str, code: str, **kwargs) -> Dict[str, Any]:
    """统一代码执行接口"""
    executors = {
        'python': PythonExecutor(),
        'nodejs': NodeJSExecutor(),
        'shell': ShellExecutor()
    }

    executor = executors.get(language.lower())
    if not executor:
        return {
            "success": False,
            "error": f"不支持的语言: {language}",
            "output": "",
            "execution_time": 0
        }

    return executor.execute(code, **kwargs)


if __name__ == "__main__":
    # 测试代码
    test_code = """
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

    result = fibonacci(10)
    print(f"斐波那契数列第10项: {result}")
    """

    result = execute_code('python', test_code)
    print(json.dumps(result, indent=2, ensure_ascii=False))