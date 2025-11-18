"""
工具执行服务
"""
import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

from app.models.tool_models import (
    ToolDefinition, ToolExecutionRequest, ToolExecutionResult,
    ToolStatus, ToolType
)
from app.services.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class ToolExecutionService:
    """工具执行服务"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.active_executions: Dict[str, asyncio.Task] = {}
        
        # 工具执行器映射
        self.executors: Dict[ToolType, Callable] = {
            ToolType.function: self._execute_function_tool,
            ToolType.http: self._execute_http_tool,
            ToolType.stdio: self._execute_stdio_tool,
            ToolType.websocket: self._execute_websocket_tool,
            ToolType.custom: self._execute_custom_tool
        }
    
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """执行工具"""
        start_time = time.time()
        request_id = request.request_id or str(uuid.uuid4())
        
        logger.info(f"Executing tool: {request.tool_id} with arguments: {request.arguments}")
        
        try:
            # 获取工具定义
            tool = self.tool_manager.get_tool(request.tool_id)
            if not tool:
                logger.error(f"Tool not found: {request.tool_id}")
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=False,
                    error="Tool not found",
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            
            logger.info(f"Found tool: {tool.name}, type: {tool.type}, status: {tool.status}")
            
            # 检查工具状态
            if tool.status != ToolStatus.active:
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=False,
                    error="Tool is not active",
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            
            # 验证参数
            validation_result = self._validate_arguments(tool, request.arguments)
            if not validation_result["valid"]:
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=False,
                    error=f"Invalid arguments: {validation_result['error']}",
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            
            # 执行工具
            executor_func = self.executors.get(tool.type)
            if not executor_func:
                logger.error(f"Unsupported tool type: {tool.type}")
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=False,
                    error=f"Unsupported tool type: {tool.type}",
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            
            logger.info(f"Executing tool with executor: {executor_func.__name__}")
            
            # 执行工具（带超时）
            try:
                if request.timeout:
                    logger.info(f"Executing with timeout: {request.timeout}s")
                    result = await asyncio.wait_for(
                        executor_func(tool, request.arguments),
                        timeout=request.timeout
                    )
                else:
                    logger.info("Executing without timeout")
                    result = await executor_func(tool, request.arguments)
                
                logger.info(f"Tool execution completed successfully, result: {result}")
                
                # 更新工具使用统计
                tool.increment_usage()
                tool.last_used = time.strftime("%Y-%m-%d %H:%M:%S")
                
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=True,
                    data=result,
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
                
            except asyncio.TimeoutError:
                return ToolExecutionResult(
                    request_id=request_id,
                    tool_id=request.tool_id,
                    success=False,
                    error="Execution timeout",
                    execution_time=time.time() - start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                )
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolExecutionResult(
                request_id=request_id,
                tool_id=request.tool_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
    
    def _validate_arguments(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具参数"""
        try:
            # 基于input_schema进行验证
            required_fields = tool.input_schema.get("required", [])
            
            for field in required_fields:
                if field not in arguments:
                    return {
                        "valid": False,
                        "error": f"Missing required field: {field}"
                    }
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    async def _execute_function_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """执行函数类型工具"""
        # 检查是否是PostgreSQL工具
        tool_server_id = tool.config.get("server_id")
        if tool_server_id == "postgres-server":
            logger.info(f"Executing PostgreSQL tool: {tool.name}")
            # 通过server_manager调用PostgreSQL工具
            if hasattr(self.tool_manager, 'server_manager') and self.tool_manager.server_manager:
                result = await self.tool_manager.server_manager.execute_postgres_tool(
                    tool.name,
                    arguments
                )
                return result
            else:
                logger.error("Server manager not available for PostgreSQL tool execution")
                return {"success": False, "error": "Server manager not available"}
        
        # 原有逻辑
        function_name = tool.config.get("function_name")
        if function_name:
            # 调用本地函数
            if function_name in globals():
                func = globals()[function_name]
                if callable(func):
                    return await asyncio.get_event_loop().run_in_executor(
                        self.executor, func, **arguments
                    )
        
        # 默认返回参数
        return arguments
    
    async def _execute_http_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """执行HTTP类型工具"""
        logger.info(f"Executing HTTP tool: {tool.name}")
        logger.info(f"Tool config: {tool.config}")
        logger.info(f"Arguments: {arguments}")
        
        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for HTTP tools")
            raise ImportError("httpx is required for HTTP tools")
        
        url = tool.config.get("url")
        method = tool.config.get("method", "GET")
        headers = tool.config.get("headers", {})
        
        logger.info(f"HTTP request - URL: {url}, Method: {method}, Headers: {headers}")
        
        if not url:
            logger.error("HTTP tool missing URL configuration")
            raise ValueError("HTTP tool missing URL configuration")
        
        # 处理参数
        if method.upper() == "GET":
            # GET请求将参数作为查询参数
            params = arguments
            data = None
            logger.info(f"GET request with params: {params}")
        else:
            # POST等请求将参数作为请求体
            params = None
            data = arguments
            logger.info(f"{method} request with data: {data}")
        
        try:
            # 检查是否是SSE类型的URL（基于工具配置或URL特征）
            is_sse = (tool.config.get("server_type") == "sse" or 
                     "sse" in url.lower() or 
                     tool.config.get("type") == "sse")
            
            if is_sse:
                logger.info("Detected SSE endpoint, using streaming approach")
                
                # 从工具ID中提取实际的MCP工具名称
                # 工具ID格式: {server_id}_{mcp_tool_name}
                tool_name = None
                if '_' in tool.id:
                    parts = tool.id.split('_', 1)
                    if len(parts) > 1:
                        tool_name = parts[1]  # 获取下划线后的部分作为工具名
                
                logger.info(f"Extracted tool name: {tool_name} from tool ID: {tool.id}")
                return await self._handle_sse_request(url, params, headers, tool_name)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Making {method.upper()} request to {url}")
                
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, params=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                logger.info(f"HTTP response status: {response.status_code}")
                logger.info(f"HTTP response headers: {dict(response.headers)}")
                
                response.raise_for_status()  # 检查HTTP错误状态码
                
                # 尝试解析JSON响应
                try:
                    result = response.json()
                    logger.info(f"HTTP response JSON: {result}")
                    return result
                except Exception as e:
                    # 如果不是JSON，返回文本内容
                    result = response.text
                    logger.info(f"HTTP response text (first 500 chars): {result[:500]}")
                    return result
                    
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in HTTP tool execution: {e}")
            raise
    
    async def _handle_sse_request(self, url: str, params: Dict[str, Any], headers: Dict[str, str], tool_name: str = None) -> Any:
        """使用MCP SSE客户端处理请求"""
        logger.info(f"Handling MCP SSE request to {url}")
        
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            # 根据文章示例，SSE URL应该是服务器的基础URL
            # 我们需要从完整URL中提取基础URL
            if url.endswith('/sse'):
                base_url = url
            else:
                # 如果URL不是以/sse结尾，我们假设这是基础URL并添加/sse
                base_url = url.rstrip('/') + '/sse'
            
            logger.info(f"Connecting to MCP SSE server at: {base_url}")
            
            # 使用sse_client连接到MCP服务器
            async with sse_client(url=base_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    logger.info("MCP SSE session established successfully")
                    
                    # 关键：必须先初始化会话
                    await session.initialize()
                    logger.info("MCP session initialized")
                    
                    # 获取可用工具列表
                    tools_result = await session.list_tools()
                    available_tools = [tool.name for tool in tools_result.tools]
                    logger.info(f"Available tools: {available_tools}")
                    
                    # 查找指定的工具
                    target_tool = None
                    if not tool_name:
                        logger.error("No tool name provided for MCP SSE request")
                        return {
                            "mcp_response": {
                                "status": "error",
                                "error": "Tool name is required for MCP SSE requests",
                                "available_tools": available_tools
                            }
                        }
                    
                    for tool in tools_result.tools:
                        if tool.name == tool_name:
                            target_tool = tool
                            break
                    
                    if not target_tool:
                        logger.warning(f"Tool '{tool_name}' not found. Available tools: {available_tools}")
                        return {
                            "mcp_response": {
                                "status": "error",
                                "error": f"Tool '{tool_name}' not found",
                                "available_tools": available_tools
                            }
                        }
                    
                    logger.info(f"Found target tool: {target_tool.name}")
                    logger.info(f"Tool description: {target_tool.description}")
                    logger.info(f"Calling tool with params: {params}")
                    
                    # 调用目标工具
                    call_result = await session.call_tool(target_tool.name, params)
                    logger.info(f"Tool call completed. Result type: {type(call_result)}")
                    
                    # 添加详细的结果调试信息
                    logger.info(f"Call result attributes: {dir(call_result)}")
                    if hasattr(call_result, 'content'):
                        logger.info(f"Call result content type: {type(call_result.content)}")
                        logger.info(f"Call result content length: {len(call_result.content) if call_result.content else 0}")
                    if hasattr(call_result, 'isError'):
                        logger.info(f"Call result isError: {call_result.isError}")
                    
                    # 处理结果
                    result_content = []
                    if hasattr(call_result, 'content') and call_result.content:
                        for content in call_result.content:
                            if hasattr(content, 'text'):
                                result_content.append({
                                    "type": "text",
                                    "text": content.text
                                })
                            else:
                                result_content.append({
                                    "type": "unknown",
                                    "content": str(content)
                                })
                    
                    return {
                        "mcp_response": {
                            "status": "success",
                            "tool_name": target_tool.name,
                            "result": result_content,
                            "is_error": getattr(call_result, 'isError', False),
                            "available_tools": available_tools
                        }
                    }
                    
        except ImportError as e:
            logger.error(f"MCP SSE import error: {e}")
            return {
                "mcp_response": {
                    "status": "error",
                    "error": f"MCP SSE not available: {str(e)}",
                    "error_type": "ImportError"
                }
            }
        except Exception as e:
            logger.error(f"MCP SSE request error: {str(e)}", exc_info=True)
            return {
                "mcp_response": {
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            }
    
    async def _execute_stdio_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """执行标准输入输出类型工具"""
        import subprocess
        
        command = tool.config.get("command")
        args = tool.config.get("args", [])
        working_dir = tool.config.get("working_dir")
        
        if not command:
            raise ValueError("STDIO tool missing command configuration")
        
        # 构建完整命令
        cmd = [command] + args
        
        # 处理输入参数
        input_data = None
        if "input" in arguments:
            input_data = str(arguments["input"]).encode()
        
        # 执行命令
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir
        )
        
        stdout, stderr = await process.communicate(input=input_data)
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")
        
        return stdout.decode()
    
    async def _execute_websocket_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """执行WebSocket类型工具"""
        # WebSocket工具执行逻辑
        # 这里可以实现WebSocket连接和消息发送
        return f"WebSocket tool {tool.name} executed with arguments: {arguments}"
    
    async def _execute_custom_tool(self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Any:
        """执行自定义类型工具"""
        # 自定义工具执行逻辑
        # 可以根据工具配置实现特定的执行逻辑
        custom_handler = tool.config.get("handler")
        if custom_handler and callable(custom_handler):
            return await custom_handler(arguments)
        
        return f"Custom tool {tool.name} executed with arguments: {arguments}"
    
    async def cancel_execution(self, request_id: str) -> bool:
        """取消工具执行"""
        if request_id in self.active_executions:
            task = self.active_executions[request_id]
            task.cancel()
            del self.active_executions[request_id]
            return True
        return False
    
    def get_active_executions(self) -> List[str]:
        """获取活跃的执行任务"""
        return list(self.active_executions.keys())
    
    async def execute_tools_batch(self, requests: List[ToolExecutionRequest]) -> List[ToolExecutionResult]:
        """批量执行工具"""
        results = []
        for request in requests:
            result = await self.execute_tool(request)
            results.append(result)
        return results
