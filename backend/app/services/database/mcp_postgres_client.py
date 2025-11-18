"""
MCP PostgreSQL客户端
封装对mcp-service PostgreSQL工具的HTTP调用
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class MCPPostgresClient:
    """
    MCP PostgreSQL客户端
    
    封装对mcp-service提供的PostgreSQL工具的调用，
    提供简洁的Python接口供Text2SQL智能体使用。
    """
    
    def __init__(self, mcp_service_url: str = None):
        """
        初始化MCP客户端
        
        Args:
            mcp_service_url: MCP服务URL，默认从环境变量读取
        """
        self.base_url = mcp_service_url or os.getenv(
            'MCP_CLIENT_URL',
            'http://localhost:8000'
        )
        if not self.base_url.endswith('/api/v1'):
            self.base_url = f"{self.base_url}/api/v1"
        
        self.server_id = "postgres-server"
        self.timeout = 60.0  # SQL查询可能较慢
        
        logger.info(f"MCP PostgreSQL客户端初始化: {self.base_url}")
    
    def _build_tool_url(self, tool_name: str) -> str:
        """构建工具调用URL"""
        return f"{self.base_url}/servers/{self.server_id}/tools/{tool_name}/call"
    
    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            httpx.HTTPError: HTTP请求失败
            Exception: 其他错误
        """
        url = self._build_tool_url(tool_name)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"arguments": arguments}
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"工具 {tool_name} 调用成功")
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP请求失败: {tool_name}, 错误: {e}")
            raise
        except Exception as e:
            logger.error(f"工具调用失败: {tool_name}, 错误: {e}", exc_info=True)
            raise
    
    async def list_tables(self) -> List[Dict[str, Any]]:
        """
        列出所有数据库表
        
        Returns:
            表信息列表，每个表包含：
            - name: 表名
            - comment: 表注释
            - row_count: 行数
            - columns_count: 列数
            
        Example:
            ```python
            tables = await client.list_tables()
            # [
            #   {"name": "companies", "comment": "公司表", "row_count": 50},
            #   ...
            # ]
            ```
        """
        result = await self._call_tool("sql_db_list_tables", {})
        
        # 处理嵌套的data结构
        data = result.get("data", result)
        
        if data.get("success"):
            return data.get("tables", [])
        else:
            logger.error(f"列出表失败: {data.get('error')}")
            return []
    
    async def get_schemas(
        self,
        table_names: List[str]
    ) -> str:
        """
        获取表结构信息
        
        Args:
            table_names: 表名列表
            
        Returns:
            格式化的表结构字符串（DDL + 样本数据）
            
        Example:
            ```python
            schema = await client.get_schemas(["companies"])
            # 返回：
            # CREATE TABLE companies (...);
            # /* 样本数据 */
            # ...
            ```
        """
        result = await self._call_tool(
            "sql_db_schema",
            {"table_names": table_names}
        )
        
        # 处理嵌套的data结构
        data = result.get("data", result)
        
        if data.get("success"):
            return data.get("schema", "")
        else:
            logger.error(f"获取Schema失败: {data.get('error')}")
            return ""
    
    async def execute_query(self, sql: str) -> Dict[str, Any]:
        """
        执行SQL查询
        
        Args:
            sql: SQL语句
            
        Returns:
            查询结果字典：
            - success: 是否成功
            - data: 查询结果（如果成功）
            - row_count: 结果行数
            - error_type: 错误类型（如果失败）
            - error_message: 错误信息（如果失败）
            - hint: 修正提示（如果有）
            - fix_suggestions: 修正建议列表（如果有）
            
        Example:
            ```python
            result = await client.execute_query("SELECT * FROM companies LIMIT 5")
            if result["success"]:
                print(f"查询成功，返回{result['row_count']}行")
                for row in result["data"]:
                    print(row)
            else:
                print(f"查询失败: {result['error_message']}")
            ```
        """
        result = await self._call_tool(
            "sql_db_query",
            {"query": sql}
        )
        
        # MCP工具返回的结果可能包装在data字段中
        if "data" in result and isinstance(result["data"], dict):
            return result["data"]
        
        return result
    
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        验证SQL语法和安全性
        
        Args:
            sql: SQL语句
            
        Returns:
            验证结果：
            - is_valid: 是否有效
            - error_message: 错误信息（如果无效）
            - suggestions: 修正建议（如果无效）
            
        Example:
            ```python
            result = await client.validate_sql("SELECT * FROM companies")
            if result["is_valid"]:
                print("SQL有效")
            else:
                print(f"SQL无效: {result['error_message']}")
            ```
        """
        result = await self._call_tool(
            "sql_db_query_checker",
            {"query": sql}
        )
        
        if "data" in result and isinstance(result["data"], dict):
            return result["data"]
        
        return result
    
    async def get_column_samples(
        self,
        table_name: str,
        column_name: str,
        limit: int = 10
    ) -> List[Any]:
        """
        获取列的样本值
        
        Args:
            table_name: 表名
            column_name: 列名
            limit: 样本数量
            
        Returns:
            样本值列表
            
        Example:
            ```python
            samples = await client.get_column_samples("companies", "industry", 10)
            # ['互联网', '电子商务', '金融科技', ...]
            ```
        """
        result = await self._call_tool(
            "get_column_samples",
            {
                "table_name": table_name,
                "column_name": column_name,
                "limit": limit
            }
        )
        
        # 处理嵌套的data结构
        data = result.get("data", result)
        
        if data.get("success"):
            return data.get("samples", [])
        else:
            logger.error(
                f"获取列样本失败: {table_name}.{column_name}, "
                f"错误: {data.get('error')}"
            )
            return []
    
    async def get_schema_graph(
        self,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取Schema图结构
        
        Args:
            keywords: 关键词列表（可选），用于筛选相关子图
            
        Returns:
            Schema图数据（包含nodes和edges）
            
        Example:
            ```python
            # 获取完整Schema图
            graph = await client.get_schema_graph()
            
            # 获取相关子图
            graph = await client.get_schema_graph(["公司", "评级"])
            ```
        """
        arguments = {}
        if keywords:
            arguments["keywords"] = keywords
        
        result = await self._call_tool("get_schema_graph", arguments)
        
        # 处理嵌套的data结构
        data = result.get("data", result)
        
        if data.get("success"):
            return data.get("graph", {})
        else:
            logger.error(f"获取Schema图失败: {data.get('error')}")
            return {}
    
    async def health_check(self) -> bool:
        """
        检查MCP服务是否可用
        
        Returns:
            是否可用
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url.replace('/api/v1', '')}/health"
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

