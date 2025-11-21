"""
重构后的MCP连接管理API
使用标准FastAPI依赖注入模式
"""
import logging
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, List, Optional, Any

from app.models.mcp_models import (
    MCPServerConfig, MCPServerInfo, ConnectionStatus
)
from app.services.mcp_client import MCPClient
from app.services.config_manager import ConfigManager
from app.core.dependencies import MCPClientDep, ConfigManagerDep

# 配置日志
logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter()

# === 连接管理 ===
@router.get("")
async def list_connections(
    client: MCPClientDep,
    status: Optional[str] = Query(None, description="连接状态筛选"),
    include_tools: bool = Query(False, description="包含工具列表")
) -> Dict[str, Any]:
    """获取连接列表"""
    logger.info(f"🔍 获取连接列表请求: status={status}, include_tools={include_tools}")

    try:
        # 状态筛选
        if status:
            logger.info(f"🔄 按状态筛选: {status}")
            try:
                connection_status = ConnectionStatus(status)
                servers = client.get_servers(connection_status)
                logger.info(f"✅ 状态筛选成功，找到 {len(servers)} 个服务器")
            except ValueError as e:
                logger.error(f"❌ 无效的连接状态: {status}, 错误: {e}")
                raise HTTPException(status_code=400, detail=f"无效的连接状态: {status}")
        else:
            logger.info("📋 获取所有服务器...")
            servers = client.get_servers()
            logger.info(f"✅ 获取到 {len(servers)} 个服务器")

        # 构建响应数据
        logger.info("🏗️ 构建响应数据...")
        servers_data = []

        for i, server in enumerate(servers):
            logger.info(f"📦 处理服务器 {i+1}/{len(servers)}: {server.config.id}")

            try:
                server_dict = {
                    "id": server.config.id,
                    "name": server.config.name,
                    "description": server.config.description,
                    "type": server.config.type,
                    "status": server.status,
                    "last_connected": server.last_connected,
                    "error_message": server.error_message,
                    "tools_count": len(server.tools),
                    "resources_count": len(server.resources),
                    "prompts_count": len(server.prompts)
                }
                logger.info(f"   - 状态: {server.status}")
                logger.info(f"   - 工具数: {len(server.tools)}")

                # 包含工具列表
                if include_tools and server.status == ConnectionStatus.CONNECTED:
                    logger.info(f"   - 包含工具列表详情...")
                    server_dict["tools"] = [tool.model_dump() for tool in server.tools]

                servers_data.append(server_dict)
                logger.info(f"✅ 服务器 {server.config.id} 处理完成")

            except Exception as server_error:
                logger.error(f"❌ 处理服务器 {server.config.id} 时出错: {server_error}")
                # 继续处理其他服务器
                continue

        logger.info("📊 获取统计信息...")
        try:
            stats = client.get_stats()
            logger.info(f"✅ 统计信息获取成功")
        except Exception as stats_error:
            logger.error(f"❌ 获取统计信息失败: {stats_error}")
            stats = {"error": str(stats_error)}

        response_data = {
            "connections": servers_data,
            "total_count": len(servers_data),
            "stats": stats
        }

        logger.info(f"🎉 连接列表请求成功: 返回 {len(servers_data)} 个连接")
        return response_data

    except HTTPException:
        # HTTP异常直接重新抛出
        raise
    except Exception as e:
        logger.error(f"💥 获取连接列表时发生未预期错误: {e}")
        logger.error(f"🔍 错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"📚 完整错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取连接列表失败: {str(e)}")


@router.get("/{connection_id}")
async def get_connection(connection_id: str, client: MCPClientDep) -> MCPServerInfo:
    """获取特定连接信息"""
    server_info = client.get_server(connection_id)
    if not server_info:
        raise HTTPException(status_code=404, detail="连接不存在")

    return server_info


@router.post("")
async def add_connection(
    config: MCPServerConfig,
    client: MCPClientDep,
    manager: ConfigManagerDep,
    auto_connect: bool = Query(True, description="是否自动连接")
) -> Dict[str, str]:
    """添加新连接"""
    try:
        # 添加到配置管理器
        if not manager.add_server(config):
            raise HTTPException(status_code=400, detail="连接已存在或添加失败")

        # 添加到MCP客户端
        if not await client.add_server(config):
            # 回滚配置
            manager.remove_server(config.id)
            raise HTTPException(status_code=500, detail="添加到MCP客户端失败")

        # 如果配置为激活状态且启用自动连接，则自动建立连接
        connection_status = "已注册"
        if config.is_active and auto_connect:
            try:
                success = await client.connect_server(config.id)
                if success:
                    connection_status = "已注册并已连接"
                else:
                    server_info = client.get_server(config.id)
                    error_msg = server_info.error_message if server_info else "未知错误"
                    connection_status = f"已注册但连接失败: {error_msg}"
            except Exception as e:
                connection_status = f"已注册但连接失败: {str(e)}"

        return {
            "message": f"连接添加成功，{connection_status}",
            "connection_id": config.id,
            "connected": connection_status.startswith("已注册并已连接")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加连接失败: {str(e)}")


@router.delete("/{connection_id}")
async def remove_connection(
    connection_id: str,
    client: MCPClientDep,
    manager: ConfigManagerDep
):
    """移除连接"""
    try:
        # 断开连接
        await client.disconnect_server(connection_id)

        # 从MCP客户端移除
        await client.remove_server(connection_id)

        # 从配置管理器移除
        manager.remove_server(connection_id)

        return {"message": "连接移除成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除连接失败: {str(e)}")


# === 连接操作 ===
@router.post("/{connection_id}/connect")
async def connect_server(connection_id: str, client: MCPClientDep):
    """连接到服务器"""
    try:
        success = await client.connect_server(connection_id)
        if success:
            return {"message": "连接成功", "connection_id": connection_id}
        else:
            server_info = client.get_server(connection_id)
            error_msg = server_info.error_message if server_info else "未知错误"
            raise HTTPException(status_code=500, detail=f"连接失败: {error_msg}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")


@router.post("/{connection_id}/disconnect")
async def disconnect_server(connection_id: str, client: MCPClientDep):
    """断开服务器连接"""
    try:
        await client.disconnect_server(connection_id)
        return {"message": "断开连接成功", "connection_id": connection_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"断开连接失败: {str(e)}")


# === 工具操作 ===
@router.get("/{connection_id}/tools")
async def get_connection_tools(connection_id: str, client: MCPClientDep) -> List[Dict[str, Any]]:
    """获取连接的工具列表"""
    # 检查连接状态
    server_info = client.get_server(connection_id)
    if not server_info:
        raise HTTPException(status_code=404, detail="连接不存在")

    if server_info.status != ConnectionStatus.CONNECTED:
        raise HTTPException(status_code=400, detail="连接未建立")

    try:
        tools = client.get_tools(connection_id)
        return [tool.model_dump() for tool in tools]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


@router.post("/{connection_id}/tools/{tool_name}/call")
async def call_tool(
    connection_id: str,
    tool_name: str,
    client: MCPClientDep,
    arguments: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """调用工具"""
    try:
        # 兼容处理：如果参数被包裹在 arguments 字段中，则提取出来
        # 这样可以支持 {"arguments": {"query": "..."}} 和 {"query": "..."} 两种格式
        actual_arguments = arguments
        if "arguments" in arguments and isinstance(arguments["arguments"], dict) and len(arguments) == 1:
             actual_arguments = arguments["arguments"]

        result = await client.call_tool(connection_id, tool_name, actual_arguments)
        return {
            "success": True,
            "result": result,
            "connection_id": connection_id,
            "tool_name": tool_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "connection_id": connection_id,
            "tool_name": tool_name
        }


# === 全局工具查询 ===
@router.get("/tools/all")
async def get_all_tools(client: MCPClientDep) -> Dict[str, Any]:
    """获取所有可用工具"""
    try:
        all_tools = client.get_tools()  # 获取所有服务器的工具
        active_servers = client.get_active_servers()

        # 按服务器分组工具
        tools_by_server = {}
        for server in active_servers:
            tools_by_server[server.config.id] = {
                "server_name": server.config.name,
                "tools": [tool.model_dump() for tool in server.tools]
            }

        return {
            "total_tools": len(all_tools),
            "active_servers": len(active_servers),
            "tools_by_server": tools_by_server,
            "all_tools": [
                {
                    **tool.model_dump(),
                    "server_id": tool.name.split('.')[0],
                    "tool_name": tool.name.split('.')[1] if '.' in tool.name else tool.name
                }
                for tool in all_tools
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


# === 统计和健康检查 ===
@router.get("/stats/summary")
async def get_stats(client: MCPClientDep) -> Dict[str, Any]:
    """获取统计信息"""
    try:
        return client.get_stats()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/health")
async def health_check(client: MCPClientDep) -> Dict[str, Any]:
    """健康检查"""
    try:
        return await client.health_check()

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# === 配置管理 ===
@router.post("/config/reload")
async def reload_config(manager: ConfigManagerDep):
    """重新加载配置"""
    try:
        manager.reload_config()
        return {"message": "配置重新加载成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载配置失败: {str(e)}")


@router.get("/config/export")
async def export_config(manager: ConfigManagerDep) -> Dict[str, Any]:
    """导出配置"""
    try:
        return manager.export_config()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")


@router.post("/config/import")
async def import_config(
    manager: ConfigManagerDep,
    config_data: Dict[str, Any] = Body(...)
):
    """导入配置"""
    try:
        success = manager.import_config(config_data)
        if success:
            return {"message": "配置导入成功"}
        else:
            raise HTTPException(status_code=400, detail="导入配置失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")