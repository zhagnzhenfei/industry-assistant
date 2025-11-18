import httpx
import logging
import os
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status

# 配置日志
logger = logging.getLogger(__name__)


class MCPServiceManager:
    """MCP服务管理器"""
    
    def __init__(self):
        # 从环境变量获取MCP服务URL，如果没有则使用默认值
        self.base_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        if not self.base_url.endswith("/api/v1"):
            self.base_url = f"{self.base_url}/api/v1"
        
        logger.info(f"MCP服务管理器初始化: base_url={self.base_url}")
    
    async def _check_connection(self) -> bool:
        """检查MCP服务连接状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url.replace('/api/v1', '')}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"MCP服务连接检查失败: {str(e)}")
            return False
    
    async def get_mcp_servers(self) -> List[Dict[str, Any]]:
        """获取MCP服务列表"""
        logger.info("开始获取MCP服务列表")
        
        # 先检查连接状态
        if not await self._check_connection():
            logger.error("MCP服务连接失败，请检查服务是否启动")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP服务连接失败，请检查服务是否启动"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/servers/?include_tools_count=true",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                servers = data.get("servers", [])
                logger.info(f"成功获取MCP服务列表: 数量={len(servers)}")
                return servers
        except httpx.ConnectError as e:
            logger.error(f"MCP服务连接失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MCP服务连接失败: {str(e)}"
            )
        except httpx.TimeoutException as e:
            logger.error(f"MCP服务请求超时: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"MCP服务请求超时: {str(e)}"
            )
        except Exception as e:
            logger.error(f"获取MCP服务列表失败: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取MCP服务列表失败: {str(e)}"
            )
    
    async def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """获取指定MCP服务的工具列表"""
        logger.info(f"开始获取MCP服务工具列表: server_id={server_id}")
        
        # 先检查连接状态
        if not await self._check_connection():
            logger.error("MCP服务连接失败，请检查服务是否启动")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP服务连接失败，请检查服务是否启动"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/servers/{server_id}/tools",
                    timeout=30.0
                )
                response.raise_for_status()
                tools = response.json()
                logger.info(f"成功获取MCP服务工具列表: server_id={server_id}, 工具数量={len(tools)}")
                return tools
        except httpx.ConnectError as e:
            logger.error(f"MCP服务连接失败: server_id={server_id}, error={str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MCP服务连接失败: {str(e)}"
            )
        except httpx.TimeoutException as e:
            logger.error(f"MCP服务请求超时: server_id={server_id}, error={str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"MCP服务请求超时: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"MCP服务不存在: server_id={server_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MCP服务不存在: server_id={server_id}"
                )
            else:
                logger.error(f"MCP服务HTTP错误: server_id={server_id}, status={e.response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"MCP服务HTTP错误: {e.response.status_code}"
                )
        except Exception as e:
            logger.error(f"获取MCP服务工具列表失败: server_id={server_id}, error={str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取MCP服务工具列表失败: {str(e)}"
            )
    
    async def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """获取指定MCP服务信息"""
        logger.debug(f"查询MCP服务信息: server_id={server_id}")
        try:
            servers = await self.get_mcp_servers()
            for server in servers:
                if server.get("id") == server_id:
                    logger.debug(f"找到MCP服务: {server.get('name', server_id)}")
                    return server
            logger.debug(f"未找到MCP服务: server_id={server_id}")
            return None
        except Exception as e:
            logger.error(f"查询MCP服务信息失败: server_id={server_id}, error={str(e)}", exc_info=True)
            return None
    
    async def build_enhanced_prompt(self, base_prompt: str, mcp_server_ids: List[str]) -> str:
        """构建增强的系统提示词，包含MCP工具信息和参数"""
        logger.info(f"开始构建增强提示词: 原始长度={len(base_prompt)}, MCP服务数量={len(mcp_server_ids)}")
        
        if not mcp_server_ids:
            logger.info("无MCP服务配置，返回原始提示词")
            return base_prompt
        
        # 构建增强的提示词
        enhanced_prompt = f"""{base_prompt}

## 工具使用能力

在这个环境中，你可以使用以下MCP工具来帮助用户解决问题：

"""
        
        # 动态获取每个服务的工具信息
        for server_id in mcp_server_ids:
            try:
                tools = await self.get_server_tools(server_id)
                enhanced_prompt += f"\n### {server_id} 服务工具列表：\n"
                
                for tool in tools:
                    tool_name = tool.get('name', 'unknown')
                    tool_description = tool.get('description', '无描述')
                    input_schema = tool.get('input_schema', {})
                    
                    enhanced_prompt += f"\n**工具名称**: {tool_name}\n"
                    enhanced_prompt += f"**工具描述**: {tool_description}\n"
                    
                    # 添加输入参数信息
                    if input_schema and 'properties' in input_schema:
                        enhanced_prompt += "**输入参数**:\n"
                        properties = input_schema['properties']
                        required = input_schema.get('required', [])
                        
                        for param_name, param_info in properties.items():
                            param_type = param_info.get('type', 'unknown')
                            param_desc = param_info.get('description', '无描述')
                            param_default = param_info.get('default')
                            is_required = param_name in required
                            
                            enhanced_prompt += f"  - `{param_name}` ({param_type})"
                            if is_required:
                                enhanced_prompt += " **[必需]**"
                            else:
                                enhanced_prompt += " [可选]"
                            
                            enhanced_prompt += f": {param_desc}"
                            
                            if param_default is not None:
                                enhanced_prompt += f" (默认值: {param_default})"
                            enhanced_prompt += "\n"
                    else:
                        enhanced_prompt += "**输入参数**: 无参数要求\n"
                    
                    enhanced_prompt += "\n"
                
            except Exception as e:
                logger.warning(f"获取服务 {server_id} 的工具信息失败: {e}")
                # 不在提示词中显示错误信息，只记录日志
                # enhanced_prompt += f"\n### {server_id} 服务工具列表：\n"
                # enhanced_prompt += f"**状态**: 工具信息获取失败，但服务可用\n\n"
                continue  # 跳过这个服务，继续处理其他服务
        
        enhanced_prompt += """
## 工具使用规则

请遵循以下规则来帮助用户：

1. **优先使用工具**: 当用户需要搜索信息、获取数据或执行特定任务时，优先考虑使用可用的MCP工具
2. **智能判断**: 根据用户问题的性质，选择合适的工具来解决问题
3. **工具组合**: 可以组合使用多个工具来完成复杂任务
4. **结果解释**: 使用工具后，请用通俗易懂的语言向用户解释结果
5. **工具限制**: 如果某个工具无法满足需求，请告知用户并提供替代方案
6. **参数正确性**: 调用工具时必须提供正确的参数，特别是必需参数

## 响应要求

- 使用中文回复用户
- 保持专业、友好的语调
- 提供准确、有用的信息
- 当需要使用工具时，明确告知用户你将使用哪个工具以及为什么
- 确保工具调用参数完整且正确

## 工具调用示例

当需要使用工具时，请按照以下格式调用：

**搜索信息示例**:
- 使用 `bing_search` 工具搜索关键词
- 参数: `query` (搜索关键词), `num_results` (结果数量，可选，默认5)

**获取网页内容示例**:
- 使用 `fetch_webpage` 工具获取网页内容
- 参数: `result_id` (从搜索返回的结果ID)

## 用户指令

"""
        
        enhanced_prompt += f"{base_prompt}\n\n现在开始！请用中文回复用户的问题，并根据需要使用可用的工具来提供最佳帮助。"
        
        logger.info(f"增强提示词构建完成: 最终长度={len(enhanced_prompt)}")
        return enhanced_prompt
    
    async def get_available_tools_for_assistant(self, mcp_server_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """获取智能体可用的所有工具"""
        logger.info(f"开始获取智能体可用工具: MCP服务数量={len(mcp_server_ids)}")
        
        tools_by_server = {}
        
        for server_id in mcp_server_ids:
            try:
                tools = await self.get_server_tools(server_id)
                tools_by_server[server_id] = tools
                logger.info(f"成功获取服务 {server_id} 的工具: 数量={len(tools)}")
            except Exception as e:
                # 记录错误但不中断其他服务的工具获取
                logger.error(f"获取服务 {server_id} 的工具列表失败: {e}", exc_info=True)
                tools_by_server[server_id] = []
        
        total_tools = sum(len(tools) for tools in tools_by_server.values())
        logger.info(f"智能体可用工具获取完成: 总工具数量={total_tools}")
        return tools_by_server
