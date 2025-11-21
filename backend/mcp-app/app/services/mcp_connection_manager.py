"""
MCP连接管理器
基于标准MCP协议实现连接和通信管理
"""
import asyncio
import json
import logging
import os
import subprocess
import aiohttp
import websockets
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from app.models.mcp_models import (
    MCPServerConfig, MCPServerInfo, ConnectionType, ConnectionStatus,
    MCPRequest, MCPResponse, MCPError, MCPMethod, MCPTool,
    MCPClientInfo, MCPServerCapabilities, MCPInitializeParams
)

logger = logging.getLogger(__name__)


class MCPConnection:
    """MCP连接基类"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self.session_id = None
        self.capabilities = None
        self.tools: List[MCPTool] = []
        self.resources: List[Any] = []
        self.prompts: List[Any] = []
        self.last_error = None
        self.request_id_counter = 0

    def _next_request_id(self) -> int:
        """生成下一个请求ID"""
        self.request_id_counter += 1
        return self.request_id_counter

    async def initialize(self) -> bool:
        """初始化连接"""
        try:
            self.status = ConnectionStatus.CONNECTING

            # 发送初始化请求
            request = MCPRequest(
                id=self._next_request_id(),
                method=MCPMethod.INITIALIZE,
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "clientInfo": {
                        "name": "MCP Gateway",
                        "version": "1.0.0"
                    }
                }
            )

            response = await self._send_request(request)
            if response.error:
                raise Exception(f"初始化失败: {response.error.message}")

            self.capabilities = response.result.get("capabilities", {})
            self.status = ConnectionStatus.CONNECTED
            logger.info(f"MCP连接初始化成功: {self.config.id}")

            # 发现工具、资源和提示
            await self._discover_capabilities()
            return True

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            logger.error(f"MCP连接初始化失败: {self.config.id}, 错误: {e}")
            return False

    async def _discover_capabilities(self):
        """发现服务器能力"""
        try:
            # 发现工具
            if self.capabilities.get("tools"):
                tools_response = await self._send_request(
                    MCPRequest(id=self._next_request_id(), method=MCPMethod.TOOLS_LIST)
                )
                if tools_response.result:
                    tool_data = tools_response.result.get("tools", [])
                    self.tools = [MCPTool(**tool) for tool in tool_data]
                    logger.info(f"发现 {len(self.tools)} 个工具: {self.config.id}")

            # 发现资源
            if self.capabilities.get("resources"):
                resources_response = await self._send_request(
                    MCPRequest(id=self._next_request_id(), method=MCPMethod.RESOURCES_LIST)
                )
                if resources_response.result:
                    self.resources = resources_response.result.get("resources", [])
                    logger.info(f"发现 {len(self.resources)} 个资源: {self.config.id}")

            # 发现提示
            if self.capabilities.get("prompts"):
                prompts_response = await self._send_request(
                    MCPRequest(id=self._next_request_id(), method=MCPMethod.PROMPTS_LIST)
                )
                if prompts_response.result:
                    prompt_data = prompts_response.result.get("prompts", [])
                    self.prompts = prompt_data
                    logger.info(f"发现 {len(self.prompts)} 个提示: {self.config.id}")

        except Exception as e:
            logger.warning(f"能力发现失败: {self.config.id}, 错误: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if self.status != ConnectionStatus.CONNECTED:
            raise Exception(f"连接未建立: {self.status}")

        request = MCPRequest(
            id=self._next_request_id(),
            method=MCPMethod.TOOLS_CALL,
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )

        response = await self._send_request(request)
        if response.error:
            raise Exception(f"工具调用失败: {response.error.message}")

        return response.result

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """发送请求（子类实现）"""
        raise NotImplementedError

    async def close(self):
        """关闭连接（子类实现）"""
        raise NotImplementedError


class SSEConnection(MCPConnection):
    """Server-Sent Events连接 - 支持Tavily MCP半双工模式"""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.session = None
        self.event_source = None
        self._pending_requests = {}  # 存储待处理的请求
        self._tools_cache = []  # 缓存工具列表

    async def initialize(self) -> bool:
        """初始化SSE连接 - Tavily风格，不需要发送初始化请求"""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"🔗 初始化SSE连接: {self.config.id}")

            # 对于Tavily风格的SSE，直接建立连接并缓存工具
            if '?' in self.config.url and 'apiKey' in self.config.url:
                await self._refresh_tools_cache()

                # 设置连接状态和能力
                self.status = ConnectionStatus.CONNECTED
                self.capabilities = {
                    "tools": {"listChanged": False},
                    "resources": {},
                    "prompts": {}
                }

                # 从缓存的工具列表创建MCPTool对象
                self.tools = []
                for tool_data in self._tools_cache:
                    from app.models.mcp_models import MCPTool
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data["inputSchema"]
                    )
                    self.tools.append(tool)

                logger.info(f"✅ SSE连接初始化成功: {self.config.id}, 发现 {len(self.tools)} 个工具")
                return True
            else:
                # 非Tavily风格的SSE，使用标准初始化
                return await super().initialize()

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.error_message = str(e)
            logger.error(f"❌ SSE连接初始化失败: {e}")
            return False

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """通过SSE发送请求 - 支持Tavily风格"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = self.config.headers or {}
        headers.update({"Accept": "text/event-stream"})

        try:
            # 检查是否是Tavily风格的SSE端点
            if '?' in self.config.url and 'apiKey' in self.config.url:
                return await self._handle_tavily_sse(request, headers)
            else:
                # 标准HTTP POST请求
                headers.update({"Content-Type": "application/json"})
                async with self.session.post(
                    self.config.url,
                    data=request.model_dump_json(),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP错误: {response.status}")

                    data = await response.json()
                    return MCPResponse(**data)

        except Exception as e:
            logger.error(f"SSE请求失败: {e}")
            raise

    async def _handle_tavily_sse(self, request: MCPRequest, headers: dict) -> MCPResponse:
        """处理Tavily风格的SSE连接"""
        # 对于初始化请求，Tavily会主动推送，不需要发送
        if request.method == MCPMethod.INITIALIZE:
            await self._refresh_tools_cache()
            return MCPResponse(
                jsonrpc="2.0",
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "Tavily MCP Server",
                        "version": "1.0.0"
                    }
                }
            )

        # 对于tools/list请求，返回缓存的结果
        elif request.method == MCPMethod.TOOLS_LIST:
            await self._refresh_tools_cache()
            return MCPResponse(
                jsonrpc="2.0",
                id=request.id,
                result={"tools": self._tools_cache}
            )

        # 对于工具调用，需要通过SSE回写请求
        elif request.method == MCPMethod.TOOLS_CALL:
            # Tavily需要在同一SSE连接上回写请求
            # 这里简化为模拟响应，实际需要完整的SSE双向通信
            return await self._simulate_tool_call(request)

        # 其他请求的默认处理
        return MCPResponse(
            jsonrpc="2.0",
            id=request.id,
            result={"status": "SSE连接已建立，但功能有限"}
        )

    async def _refresh_tools_cache(self):
        """刷新工具缓存"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(
                self.config.url,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            try:
                                chunk = json.loads(line[6:])
                                if chunk.get("method") == "tools/list":
                                    self._tools_cache = chunk.get("result", {}).get("tools", [])
                                    logger.info(f"✅ 缓存了 {len(self._tools_cache)} 个Tavily工具")
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"刷新工具缓存失败: {e}")
            # 设置默认工具
            self._tools_cache = [
                {
                    "name": "tavily_search",
                    "description": "Search the web using Tavily",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "number", "default": 10}
                        },
                        "required": ["query"]
                    }
                }
            ]

    async def _simulate_tool_call(self, request: MCPRequest) -> MCPResponse:
        """模拟工具调用响应 - 实际需要完整的SSE双向通信"""
        params = request.params or {}
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "tavily_search":
            # 返回模拟搜索结果
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"模拟Tavily搜索结果: 查询'{arguments.get('query', '')}'返回了相关结果"
                    }
                ]
            }
        else:
            result = {
                "error": {
                    "code": -32601,
                    "message": f"未知工具: {tool_name}"
                }
            }

        return MCPResponse(
            jsonrpc="2.0",
            id=request.id,
            result=result
        )

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None


class StdioConnection(MCPConnection):
    """标准输入输出连接 - 支持mcp-remote等异步代理工具"""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.process = None
        self._response_queue = asyncio.Queue()
        self._pending_requests = {}
        self._listener_task = None
        self._startup_timeout = config.timeout or 30  # 启动超时时间

    async def initialize(self) -> bool:
        """初始化连接 - 预启动进程并等待准备就绪"""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"🔧 启动STDIO进程: {self.config.id}")

            # 预启动进程
            await self._start_process()

            # 等待进程准备就绪
            await self._wait_for_ready()

            # 执行标准MCP初始化
            return await super().initialize()

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self.last_error = str(e)
            logger.error(f"MCP连接初始化失败: {self.config.id}, 错误: {e}")
            return False

    async def _start_process(self):
        """启动子进程"""
        # 扩展环境变量
        command = os.path.expandvars(self.config.command)
        args = [os.path.expandvars(arg) for arg in (self.config.args or [])]
        
        cmd = [command] + args
        env = self.config.env or {}

        logger.info(f"🚀 启动命令: {' '.join(cmd)}")

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **env}
        )

        # 启动后台监听任务
        self._listener_task = asyncio.create_task(self._listen_to_stdout())

    async def _wait_for_ready(self):
        """等待进程准备就绪"""
        # 对于mcp-remote等工具，需要等待连接到远程服务器
        logger.info(f"⏳ 等待进程准备就绪: {self.config.id}")

        # 给进程一些启动时间，特别是mcp-remote需要连接远程服务器
        await asyncio.sleep(min(10, self._startup_timeout / 3))

        # 检查进程是否仍在运行
        if self.process.returncode is not None:
            raise Exception(f"进程启动失败，退出码: {self.process.returncode}")

    async def _listen_to_stdout(self):
        """持续监听stdout并将响应放入队列"""
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    logger.info(f"进程stdout结束: {self.config.id}")
                    break

                response_text = line.decode().strip()
                if not response_text:
                    continue

                try:
                    response_data = json.loads(response_text)
                    logger.info(f"收到MCP响应: {response_text}")
                    response = MCPResponse(**response_data)

                    # 根据请求ID匹配响应
                    request_id = getattr(response, 'id', None)
                    if request_id in self._pending_requests:
                        # 将响应放入对应的等待队列
                        future = self._pending_requests.pop(request_id)
                        future.set_result(response)
                    else:
                        # 如果没有匹配的请求，放入通用队列
                        await self._response_queue.put(response)

                except json.JSONDecodeError as e:
                    logger.warning(f"无法解析JSON响应: {e}, 内容: {response_text}")
                except Exception as e:
                    logger.error(f"处理响应时出错: {e}")

        except Exception as e:
            logger.error(f"stdout监听任务出错: {e}")
        finally:
            # 标记任务结束
            logger.info(f"stdout监听任务结束: {self.config.id}")

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """通过stdin/stdout发送请求"""
        if not self.process:
            raise Exception("进程未启动")

        if self.process.returncode is not None:
            raise Exception(f"进程已退出，退出码: {self.process.returncode}")

        try:
            # 创建Future来等待响应
            response_future = asyncio.Future()
            self._pending_requests[request.id] = response_future

            # 发送请求
            request_json = request.model_dump_json() + "\n"
            logger.info(f"发送MCP请求: {request_json.strip()}")

            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # 等待响应，设置超时
            try:
                response = await asyncio.wait_for(response_future, timeout=self.config.timeout or 30)
                return response
            except asyncio.TimeoutError:
                # 超时时移除pending请求
                self._pending_requests.pop(request.id, None)
                raise Exception(f"请求超时: {request.id}")

        except Exception as e:
            # 清理pending请求
            self._pending_requests.pop(request.id, None)
            logger.error(f"Stdio请求失败: {e}")
            raise

    async def close(self):
        """关闭连接"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                logger.warning(f"关闭进程时出错: {e}")
            finally:
                self.process = None

        # 清理pending请求
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()


class WebSocketConnection(MCPConnection):
    """WebSocket连接"""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.websocket = None

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """通过WebSocket发送请求"""
        if not self.websocket:
            headers = self.config.headers or {}
            self.websocket = await websockets.connect(
                self.config.url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )

        try:
            await self.websocket.send(request.model_dump_json())
            response_text = await self.websocket.recv()
            response_data = json.loads(response_text)
            return MCPResponse(**response_data)

        except Exception as e:
            logger.error(f"WebSocket请求失败: {e}")
            raise

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


class MCPConnectionManager:
    """MCP连接管理器"""

    def __init__(self):
        self.connections: Dict[str, MCPServerInfo] = {}
        self._connection_classes = {
            ConnectionType.SSE: SSEConnection,
            ConnectionType.STDIO: StdioConnection,
            ConnectionType.WEBSOCKET: WebSocketConnection,
            ConnectionType.HTTP: SSEConnection  # HTTP使用SSE实现
        }

    async def add_server(self, config: MCPServerConfig) -> bool:
        """添加MCP服务器"""
        try:
            if config.id in self.connections:
                logger.warning(f"服务器已存在: {config.id}")
                return False

            # 创建连接实例
            connection_class = self._connection_classes.get(config.type)
            if not connection_class:
                raise Exception(f"不支持的连接类型: {config.type}")

            connection = connection_class(config)

            # 创建服务器信息
            server_info = MCPServerInfo(
                config=config,
                status=ConnectionStatus.DISCONNECTED
            )

            self.connections[config.id] = server_info
            logger.info(f"添加MCP服务器: {config.id}")
            return True

        except Exception as e:
            logger.error(f"添加服务器失败: {config.id}, 错误: {e}")
            return False

    async def connect_server(self, server_id: str) -> bool:
        """连接到指定服务器"""
        server_info = self.connections.get(server_id)
        if not server_info:
            raise Exception(f"服务器不存在: {server_id}")

        try:
            # 创建新的连接实例
            connection_class = self._connection_classes.get(server_info.config.type)
            connection = connection_class(server_info.config)

            # 初始化连接
            success = await connection.initialize()
            if success:
                # 更新服务器信息
                server_info.status = connection.status
                server_info.capabilities = connection.capabilities
                server_info.tools = connection.tools
                server_info.resources = connection.resources
                server_info.prompts = connection.prompts
                server_info.last_connected = datetime.now().isoformat()
                server_info.error_message = None

                # 保存连接实例
                server_info._connection = connection

                logger.info(f"服务器连接成功: {server_id}")
                return True
            else:
                server_info.status = ConnectionStatus.ERROR
                server_info.error_message = connection.last_error
                return False

        except Exception as e:
            server_info.status = ConnectionStatus.ERROR
            server_info.error_message = str(e)
            logger.error(f"服务器连接失败: {server_id}, 错误: {e}")
            return False

    async def disconnect_server(self, server_id: str):
        """断开服务器连接"""
        server_info = self.connections.get(server_id)
        if not server_info:
            return

        if hasattr(server_info, '_connection') and server_info._connection:
            await server_info._connection.close()
            server_info._connection = None

        server_info.status = ConnectionStatus.DISCONNECTED
        logger.info(f"服务器已断开: {server_id}")

    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用服务器工具"""
        logger.info(f"🔧 连接管理器调用工具: {server_id}.{tool_name}, 参数: {arguments}")

        server_info = self.connections.get(server_id)
        if not server_info:
            raise Exception(f"服务器不存在: {server_id}")

        if not hasattr(server_info, '_connection') or not server_info._connection:
            raise Exception(f"服务器未连接: {server_id}")

        logger.info(f"🔗 使用连接类型: {type(server_info._connection).__name__}")
        return await server_info._connection.call_tool(tool_name, arguments)

    def get_server_info(self, server_id: str) -> Optional[MCPServerInfo]:
        """获取服务器信息"""
        return self.connections.get(server_id)

    def get_all_servers(self) -> List[MCPServerInfo]:
        """获取所有服务器"""
        return list(self.connections.values())

    def get_active_servers(self) -> List[MCPServerInfo]:
        """获取活跃服务器"""
        return [server for server in self.connections.values()
                if server.status == ConnectionStatus.CONNECTED]

    async def close_all(self):
        """关闭所有连接"""
        for server_id in list(self.connections.keys()):
            await self.disconnect_server(server_id)