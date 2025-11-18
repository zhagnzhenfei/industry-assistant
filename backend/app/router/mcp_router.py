"""
MCP服务管理路由
提供MCP服务列表、工具列表等接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
import aiohttp
import os
import logging
from datetime import datetime

from service.auth_service import get_current_user
from models.user_models import User

# 独立的MCP服务器模型定义（保持解耦合）
from pydantic import BaseModel, Field
from enum import Enum

class ServerType(str, Enum):
    sse = "sse"
    stdio = "stdio"
    http = "http"
    websocket = "websocket"

class ServerStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    error = "error"
    connecting = "connecting"

class MCPServer(BaseModel):
    id: str = Field(..., description="服务器唯一标识")
    name: str = Field(..., description="服务器名称")
    description: Optional[str] = Field(default=None, description="服务器描述")
    type: ServerType = Field(..., description="服务器类型")
    url: Optional[str] = Field(default=None, description="服务器URL")
    command: Optional[str] = Field(default=None, description="启动命令")
    args: Optional[List[str]] = Field(default_factory=list, description="命令参数")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="环境变量")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="HTTP头部")
    is_active: bool = Field(default=True, description="是否激活")
    status: ServerStatus = Field(default=ServerStatus.inactive, description="服务器状态")
    timeout: int = Field(default=60, description="超时时间（秒）")
    version: str = Field(default="1.0.0", description="版本")
    author: Optional[str] = Field(default=None, description="作者")
    tags: List[str] = Field(default_factory=list, description="标签")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/servers")
async def get_mcp_servers(
    include_tools_count: bool = Query(False, description="包含工具数量统计"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取MCP服务器列表"""
    try:
        # 从环境变量获取MCP客户端URL
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        
        # 构建请求URL
        url = f"{mcp_client_url}/api/v1/servers/"
        if include_tools_count:
            url += "?include_tools_count=true"
        
        logger.info(f"获取MCP服务器列表: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"成功获取MCP服务器列表，数量: {result.get('total_count', 0)}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"MCP客户端返回错误: {response.status}, {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"获取MCP服务器列表失败: {error_text}"
                    )
                    
    except Exception as e:
        logger.error(f"获取MCP服务器列表异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取MCP服务器列表失败: {str(e)}")

@router.get("/servers/{server_id}")
async def get_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取特定MCP服务器信息"""
    try:
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        url = f"{mcp_client_url}/api/v1/servers/{server_id}"
        
        logger.info(f"获取MCP服务器信息: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail="MCP服务器不存在")
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"获取MCP服务器信息失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取MCP服务器信息异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取MCP服务器信息失败: {str(e)}")

@router.get("/servers/{server_id}/tools")
async def get_mcp_server_tools(
    server_id: str,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """获取特定MCP服务器的工具列表"""
    try:
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        url = f"{mcp_client_url}/api/v1/servers/{server_id}/tools"
        
        logger.info(f"获取MCP服务器工具列表: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail="MCP服务器不存在")
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"获取MCP服务器工具列表失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取MCP服务器工具列表异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取MCP服务器工具列表失败: {str(e)}")

@router.post("/servers/{server_id}/test")
async def test_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """测试MCP服务器连接"""
    try:
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        url = f"{mcp_client_url}/api/v1/servers/{server_id}/test"
        
        logger.info(f"测试MCP服务器连接: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"测试MCP服务器连接失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试MCP服务器连接异常: {e}")
        raise HTTPException(status_code=500, detail=f"测试MCP服务器连接失败: {str(e)}")

@router.delete("/servers/{server_id}")
async def remove_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """删除MCP服务器"""
    try:
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        url = f"{mcp_client_url}/api/v1/servers/{server_id}"
        
        logger.info(f"删除MCP服务器: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"成功删除MCP服务器 {server_id}")
                    return result
                elif response.status == 404:
                    raise HTTPException(status_code=404, detail="MCP服务器不存在")
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"删除MCP服务器失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除MCP服务器异常: {e}")
        raise HTTPException(status_code=500, detail=f"删除MCP服务器失败: {str(e)}")

@router.post("/servers")
async def create_mcp_server(
    server: MCPServer,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """创建MCP服务器"""
    try:
        mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
        url = f"{mcp_client_url}/api/v1/servers/"
        
        # 设置创建时间和初始状态
        server_data = server.model_dump()
        server_data["created_at"] = datetime.now().isoformat()
        
        # 根据is_active字段设置初始状态
        if server.is_active:
            server_data["status"] = ServerStatus.connecting.value  # 如果要激活，先设为连接中
            logger.info(f"服务器 {server.id} 设置为激活，将尝试连接")
        else:
            server_data["status"] = ServerStatus.inactive.value  # 如果不激活，设为inactive
            logger.info(f"服务器 {server.id} 设置为不激活")
        
        logger.info(f"创建MCP服务器: {url}, 服务器ID: {server.id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                json=server_data, 
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"成功创建MCP服务器 {server.id}")
                    
                    # 如果服务器设置为激活，尝试测试连接
                    if server.is_active:
                        try:
                            # 这里调用MCP客户端的测试连接接口
                            test_url = f"{mcp_client_url}/api/v1/servers/{server.id}/test"
                            async with session.post(test_url, timeout=aiohttp.ClientTimeout(total=30)) as test_response:
                                if test_response.status == 200:
                                    test_result = await test_response.json()
                                    if test_result.get("connected", False):
                                        logger.info(f"MCP服务器 {server.id} 连接测试成功，状态将更新为active")
                                        
                                        # 连接成功后，触发针对该服务器的工具发现
                                        try:
                                            discover_url = f"{mcp_client_url}/api/v1/tools/discover/{server.id}"
                                            async with session.post(discover_url, timeout=aiohttp.ClientTimeout(total=60)) as discover_response:
                                                if discover_response.status == 200:
                                                    discover_result = await discover_response.json()
                                                    discovered_count = discover_result.get("discovered_count", 0)
                                                    logger.info(f"MCP服务器 {server.id} 工具发现完成，发现 {discovered_count} 个工具")
                                                else:
                                                    logger.warning(f"MCP服务器 {server.id} 工具发现请求失败: {discover_response.status}")
                                        except Exception as discover_error:
                                            logger.warning(f"MCP服务器 {server.id} 工具发现异常: {discover_error}")
                                    else:
                                        logger.warning(f"MCP服务器 {server.id} 连接测试失败")
                                else:
                                    logger.warning(f"MCP服务器 {server.id} 连接测试请求失败: {test_response.status}")
                        except Exception as test_error:
                            logger.warning(f"MCP服务器 {server.id} 连接测试异常: {test_error}")
                    
                    return result
                elif response.status == 400:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"创建MCP服务器失败: {error_text}"
                    )
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"创建MCP服务器失败: {error_text}"
                    )
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建MCP服务器异常: {e}")
        raise HTTPException(status_code=500, detail=f"创建MCP服务器失败: {str(e)}")
