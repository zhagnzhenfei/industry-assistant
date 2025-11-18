"""
MCP工具调用客户端
连接到MCP服务并调用各种工具
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP工具调用客户端 - 连接到MCP服务"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def health_check(self) -> Dict[str, Any]:
        """检查MCP服务健康状态"""
        if not self.session:
            raise RuntimeError("MCPClient must be used in async context manager")

        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Health check failed with status: {response.status}")
        except Exception as e:
            logger.error(f"MCP服务健康检查失败: {e}")
            raise

    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        if not self.session:
            raise RuntimeError("MCPClient must be used in async context manager")

        try:
            async with self.session.get(f"{self.base_url}/api/v1/tools") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Get tools failed with status: {response.status}")
        except Exception as e:
            logger.error(f"获取工具列表失败: {e}")
            raise

    async def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具"""
        if not self.session:
            raise RuntimeError("MCPClient must be used in async context manager")

        try:
            payload = {
                "tool_id": tool_id,
                "arguments": arguments
            }

            logger.info(f"调用MCP工具: {tool_id}, 参数: {arguments}")

            async with self.session.post(
                f"{self.base_url}/api/v1/execution/execute",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"工具调用成功: {tool_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"工具调用失败: {tool_id}, 状态: {response.status}, 错误: {error_text}")
                    raise Exception(f"Tool execution failed: {error_text}")

        except Exception as e:
            logger.error(f"调用MCP工具失败 {tool_id}: {e}")
            raise

    async def call_tool_with_retry(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """带重试机制的工具调用"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self.call_tool(tool_id, arguments)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"工具调用失败，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"工具调用最终失败 {tool_id}: {e}")

        raise last_error

    def validate_tool_result(self, result: Dict[str, Any]) -> bool:
        """验证工具返回结果"""
        if not isinstance(result, dict):
            return False

        # 检查是否包含结果字段
        if "result" not in result:
            return False

        # 检查结果是否为None
        result_value = result["result"]
        if result_value is None:
            return False

        # 检查结果是否为空字符串或空列表
        if isinstance(result_value, (str, list, dict)) and not result_value:
            return False

        return True

    async def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """获取特定工具的详细信息"""
        tools = await self.get_tools()
        for tool in tools:
            if tool.get("id") == tool_id:
                return tool
        return None

    # 便捷方法：常用工具的快速调用
    async def search_files(self, pattern: str, search_path: str = ".") -> Dict[str, Any]:
        """搜索文件"""
        return await self.call_tool_with_retry(
            "file_search",
            {"pattern": pattern, "search_path": search_path}
        )

    async def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件"""
        return await self.call_tool_with_retry(
            "file_reader",
            {"file_path": file_path, "encoding": encoding}
        )

    async def write_file(self, file_path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
        """写入文件"""
        return await self.call_tool_with_retry(
            "file_writer",
            {
                "file_path": file_path,
                "content": content,
                "create_dirs": create_dirs
            }
        )

    async def execute_python(self, code: str) -> Dict[str, Any]:
        """执行Python代码"""
        return await self.call_tool_with_retry(
            "python_executor",
            {"code": code, "include_output": True}
        )

    async def git_commit(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Git提交"""
        args = {"message": message}
        if files:
            args["files"] = files
        return await self.call_tool_with_retry("git_commit", args)


async def test_mcp_client():
    """测试MCP客户端功能"""
    async with MCPClient() as client:
        # 1. 健康检查
        health = await client.health_check()
        print(f"MCP服务状态: {health}")

        # 2. 获取工具列表
        tools = await client.get_tools()
        print(f"可用工具数量: {len(tools)}")

        # 3. 测试文件搜索
        try:
            result = await client.search_files("*.py", ".")
            print(f"文件搜索结果: {result}")
        except Exception as e:
            print(f"文件搜索测试失败: {e}")

        # 4. 测试Python执行
        try:
            result = await client.execute_python("print('Hello from Agent!')")
            print(f"Python执行结果: {result}")
        except Exception as e:
            print(f"Python执行测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_mcp_client())