"""
PostgreSQL MCP服务器
提供标准SQL工具和增强工具，对齐LangChain命名规范
"""
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.db_manager import DatabaseManager
from app.core.schema_graph import SchemaGraph
from app.models.tool_models import (
    MCPServer,
    ServerType,
    ServerStatus,
    ToolDefinition,
    ToolType,
    ToolStatus
)

logger = logging.getLogger(__name__)


class PostgreSQLServer:
    """PostgreSQL MCP服务器"""
    
    def __init__(
        self,
        server_id: str = "postgres-server",
        db_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化PostgreSQL服务器
        
        Args:
            server_id: 服务器ID
            db_config: 数据库配置
        """
        self.server_id = server_id
        self.db_config = db_config or {}
        
        # 初始化组件
        self.db_manager = DatabaseManager(
            host=self.db_config.get('host'),
            port=self.db_config.get('port'),
            user=self.db_config.get('user'),
            password=self.db_config.get('password'),
            database=self.db_config.get('database'),
            max_connections=self.db_config.get('max_connections', 10)
        )
        
        self.schema_graph = SchemaGraph()
        self._initialized = False
        
        logger.info(f"PostgreSQL MCP服务器创建: {server_id}")
    
    async def initialize(self):
        """初始化服务器（连接数据库，构建Schema图）"""
        if self._initialized:
            logger.warning("服务器已初始化，跳过")
            return
        
        try:
            # 连接数据库
            await self.db_manager.connect()
            
            # 构建Schema图
            await self.schema_graph.build_from_db(self.db_manager)
            
            self._initialized = True
            logger.info("PostgreSQL MCP服务器初始化成功")
            
        except Exception as e:
            logger.error(f"服务器初始化失败: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """关闭服务器"""
        await self.db_manager.close()
        logger.info("PostgreSQL MCP服务器已关闭")
    
    def get_server_info(self) -> MCPServer:
        """
        获取服务器信息
        
        Returns:
            MCPServer对象
        """
        stats = self.schema_graph.get_statistics() if self._initialized else {}
        
        return MCPServer(
            id=self.server_id,
            name="PostgreSQL Database Server",
            description="PostgreSQL数据库访问服务器，提供SQL查询和Schema信息工具",
            type=ServerType.http,
            status=ServerStatus.active if self._initialized else ServerStatus.inactive,
            config={
                "database": self.db_config.get('database', 'unknown'),
                "host": self.db_config.get('host', 'unknown'),
                "tables_count": stats.get('table_count', 0),
                "initialized": self._initialized
            },
            tags=["database", "sql", "postgres", "text2sql"],
            tools_count=len(self.get_tools())
        )
    
    def get_tools(self) -> List[ToolDefinition]:
        """
        获取所有工具定义
        
        Returns:
            工具定义列表
        """
        return [
            # 标准SQL工具（对齐LangChain）
            self._get_list_tables_tool(),
            self._get_schema_tool(),
            self._get_query_tool(),
            self._get_query_checker_tool(),
            
            # 增强工具
            self._get_schema_graph_tool(),
            self._get_column_samples_tool(),
        ]
    
    def _get_list_tables_tool(self) -> ToolDefinition:
        """sql_db_list_tables工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:sql_db_list_tables",
            name="sql_db_list_tables",
            description=(
                "列出数据库中所有可用的表。返回表名、注释、行数和列数。"
                "使用此工具了解数据库结构，选择相关的表。"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "comment": {"type": "string"},
                                "row_count": {"type": "integer"},
                                "columns_count": {"type": "integer"}
                            }
                        }
                    }
                }
            },
            tags=["sql", "schema", "database"],
            category="database",
            status=ToolStatus.active
        )
    
    def _get_schema_tool(self) -> ToolDefinition:
        """sql_db_schema工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:sql_db_schema",
            name="sql_db_schema",
            description=(
                "获取指定表的详细结构信息，包括：\n"
                "- CREATE TABLE语句（含列注释）\n"
                "- 前3行示例数据\n"
                "- 列的样本值\n"
                "- 主键、外键和索引信息\n"
                "使用此工具了解表的详细结构，以便编写正确的SQL。"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {
                    "table_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "表名列表，如 [\"companies\", \"research_reports\"]"
                    }
                },
                "required": ["table_names"]
            },
            output_schema={
                "type": "string",
                "description": "格式化的表结构信息（DDL + 样本数据）"
            },
            tags=["sql", "schema", "database"],
            category="database",
            status=ToolStatus.active
        )
    
    def _get_query_tool(self) -> ToolDefinition:
        """sql_db_query工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:sql_db_query",
            name="sql_db_query",
            description=(
                "执行SQL查询语句（只读）。\n"
                "⚠️ 安全限制：\n"
                "- 只允许SELECT语句\n"
                "- 自动添加LIMIT限制（最多1000行）\n"
                "- 查询超时30秒\n"
                "如果查询失败，会返回详细的错误信息和修正建议。"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL查询语句，如 \"SELECT * FROM companies WHERE industry = '互联网'\""
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "data": {"type": "array"},
                    "row_count": {"type": "integer"},
                    "error_message": {"type": "string"},
                    "fix_suggestions": {"type": "array"}
                }
            },
            tags=["sql", "query", "database"],
            category="database",
            status=ToolStatus.active
        )
    
    def _get_query_checker_tool(self) -> ToolDefinition:
        """sql_db_query_checker工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:sql_db_query_checker",
            name="sql_db_query_checker",
            description=(
                "验证SQL查询的语法和安全性，但不执行。\n"
                "用于在执行前检查SQL是否符合规范。"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要验证的SQL语句"
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "error_message": {"type": "string"},
                    "suggestions": {"type": "array"}
                }
            },
            tags=["sql", "validation"],
            category="database",
            status=ToolStatus.active
        )
    
    def _get_schema_graph_tool(self) -> ToolDefinition:
        """get_schema_graph工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:get_schema_graph",
            name="get_schema_graph",
            description=(
                "获取数据库Schema的图结构表示。\n"
                "返回表和列的关系图，可用于：\n"
                "- 理解表之间的关系\n"
                "- 查找相关的表\n"
                "- 辅助JOIN查询"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "关键词列表，用于筛选相关的子图"
                    }
                },
                "required": []
            },
            output_schema={
                "type": "object",
                "description": "图结构数据（JSON格式）"
            },
            tags=["schema", "graph", "relationship"],
            category="database",
            status=ToolStatus.active
        )
    
    def _get_column_samples_tool(self) -> ToolDefinition:
        """get_column_samples工具定义"""
        return ToolDefinition(
            id=f"{self.server_id}:get_column_samples",
            name="get_column_samples",
            description=(
                "获取指定列的样本值。\n"
                "用于了解列的实际数据内容和格式。"
            ),
            version="1.0.0",
            type=ToolType.function,
            config={
                "server_id": self.server_id
            },
            input_schema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名"
                    },
                    "column_name": {
                        "type": "string",
                        "description": "列名"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "样本数量",
                        "default": 10
                    }
                },
                "required": ["table_name", "column_name"]
            },
            output_schema={
                "type": "array",
                "items": {"type": "string"},
                "description": "样本值列表"
            },
            tags=["data", "samples"],
            category="database",
            status=ToolStatus.active
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            执行结果
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "服务器未初始化，请先调用initialize()"
            }
        
        logger.info(f"执行工具: {tool_name}, 参数: {arguments}")
        
        try:
            # 路由到对应的工具处理函数
            if tool_name == "sql_db_list_tables":
                return await self._handle_list_tables()
            
            elif tool_name == "sql_db_schema":
                return await self._handle_schema(arguments)
            
            elif tool_name == "sql_db_query":
                return await self._handle_query(arguments)
            
            elif tool_name == "sql_db_query_checker":
                return await self._handle_query_checker(arguments)
            
            elif tool_name == "get_schema_graph":
                return await self._handle_schema_graph(arguments)
            
            elif tool_name == "get_column_samples":
                return await self._handle_column_samples(arguments)
            
            else:
                return {
                    "success": False,
                    "error": f"未知工具: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}, 错误: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution_error"
            }
    
    async def _handle_list_tables(self) -> Dict[str, Any]:
        """处理sql_db_list_tables"""
        tables = await self.db_manager.get_tables_info()
        
        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }
    
    async def _handle_schema(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理sql_db_schema"""
        table_names = arguments.get('table_names', [])
        
        if not table_names:
            return {
                "success": False,
                "error": "table_names参数不能为空"
            }
        
        result_parts = []
        
        for table_name in table_names:
            try:
                schema = await self.db_manager.get_table_schema(
                    table_name,
                    include_samples=True,
                    sample_limit=3
                )
                
                # 格式化为类似DDL的字符串
                formatted = self._format_schema(schema)
                result_parts.append(formatted)
                
            except Exception as e:
                result_parts.append(f"-- 获取表 {table_name} 失败: {str(e)}")
        
        return {
            "success": True,
            "schema": "\n\n".join(result_parts)
        }
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """格式化Schema为可读字符串"""
        lines = []
        
        # 表名和注释
        lines.append(f"-- Table: {schema['table_name']}")
        if schema.get('comment'):
            lines.append(f"-- {schema['comment']}")
        lines.append("")
        
        # CREATE TABLE语句
        lines.append(f"CREATE TABLE {schema['table_name']} (")
        
        col_lines = []
        for col in schema['columns']:
            col_def = f"    {col['name']} {col['type']}"
            if col.get('not_null'):
                col_def += " NOT NULL"
            if col.get('default_value'):
                col_def += f" DEFAULT {col['default_value']}"
            
            # 添加注释
            if col.get('comment'):
                col_def += f"  -- {col['comment']}"
            
            col_lines.append(col_def)
        
        # 主键
        if schema.get('primary_keys'):
            pk_cols = ', '.join(schema['primary_keys'])
            col_lines.append(f"    PRIMARY KEY ({pk_cols})")
        
        lines.append(",\n".join(col_lines))
        lines.append(");")
        lines.append("")
        
        # 外键
        if schema.get('foreign_keys'):
            lines.append("-- Foreign Keys:")
            for fk in schema['foreign_keys']:
                lines.append(
                    f"-- {fk['column_name']} -> "
                    f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
                )
            lines.append("")
        
        # 示例数据
        if schema.get('sample_data'):
            lines.append(f"/* {len(schema['sample_data'])} sample rows:")
            
            # 格式化为表格
            if schema['sample_data']:
                # 列名
                columns = list(schema['sample_data'][0].keys())
                lines.append(" | ".join(columns))
                
                # 数据行
                for row in schema['sample_data']:
                    values = [str(row.get(col, '')) for col in columns]
                    lines.append(" | ".join(values))
            
            lines.append("*/")
            lines.append("")
        
        # 列样本值
        lines.append("/* Column sample values:")
        for col in schema['columns']:
            col_name = col['name']
            # 这里可以添加实际的样本值，暂时省略
            lines.append(f"- {col_name}: [sample values would be here]")
        lines.append("*/")
        
        return "\n".join(lines)
    
    async def _handle_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理sql_db_query"""
        query = arguments.get('query', '')
        
        if not query:
            return {
                "success": False,
                "error": "query参数不能为空"
            }
        
        # 执行查询
        result = await self.db_manager.execute_query(query)
        
        return result
    
    async def _handle_query_checker(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理sql_db_query_checker"""
        query = arguments.get('query', '')
        
        if not query:
            return {
                "is_valid": False,
                "error_message": "query参数不能为空"
            }
        
        # 验证SQL
        is_valid, error_msg = self.db_manager.validate_sql_safety(query)
        
        if is_valid:
            return {
                "is_valid": True,
                "message": "SQL验证通过"
            }
        else:
            return {
                "is_valid": False,
                "error_message": error_msg,
                "suggestions": [
                    "只允许SELECT查询",
                    "检查SQL语法",
                    "确认表和列名正确"
                ]
            }
    
    async def _handle_schema_graph(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理get_schema_graph"""
        keywords = arguments.get('keywords', [])
        
        if keywords:
            # 返回子图
            subgraph = self.schema_graph.find_relevant_subgraph(keywords)
            tables = self.schema_graph.get_tables_from_subgraph(subgraph)
            graph_data = subgraph  # NetworkX图对象
            
            return {
                "success": True,
                "graph": self.schema_graph.to_dict(),  # 完整图
                "filtered_tables": tables,
                "statistics": self.schema_graph.get_statistics()
            }
        else:
            # 返回完整图
            return {
                "success": True,
                "graph": self.schema_graph.to_dict(),
                "statistics": self.schema_graph.get_statistics()
            }
    
    async def _handle_column_samples(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理get_column_samples"""
        table_name = arguments.get('table_name')
        column_name = arguments.get('column_name')
        limit = arguments.get('limit', 10)
        
        if not table_name or not column_name:
            return {
                "success": False,
                "error": "table_name和column_name参数是必需的"
            }
        
        try:
            samples = await self.db_manager.get_column_samples(
                table_name,
                column_name,
                limit
            )
            
            return {
                "success": True,
                "table": table_name,
                "column": column_name,
                "samples": samples,
                "count": len(samples)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

