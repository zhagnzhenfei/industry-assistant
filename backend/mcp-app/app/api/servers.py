"""
MCP服务器管理API
"""
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, List, Optional, Any
from app.models.tool_models import MCPServer, ServerStatus, ServerType, ToolDefinition
from app.services.server_manager import ServerManager

router = APIRouter()

# 依赖注入
server_manager: Optional[ServerManager] = None
tool_manager = None

@router.post("")
async def add_server(server: MCPServer):
    """添加MCP服务器"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"尝试添加MCP服务器: ID={server.id}, 名称={server.name}, 类型={server.type}")
    
    if not server_manager:
        logger.error("Server manager not initialized")
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    success = server_manager.add_server(server)
    if success:
        logger.info(f"成功添加MCP服务器: {server.id}")
        return {"message": "Server added successfully", "server_id": server.id}
    else:
        logger.warning(f"添加MCP服务器失败: {server.id} (可能已存在)")
        raise HTTPException(status_code=400, detail="Failed to add server or server already exists")

@router.get("")
async def list_servers(
    type: Optional[str] = Query(None, description="服务器类型"),
    status: Optional[str] = Query(None, description="服务器状态"),
    active_only: bool = Query(False, description="仅显示活跃服务器"),
    include_tools_count: bool = Query(False, description="包含工具数量统计")
) -> Dict[str, Any]:
    """列出MCP服务器"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"获取服务器列表: type={type}, status={status}, active_only={active_only}, include_tools_count={include_tools_count}")
    
    if not server_manager:
        logger.error("Server manager not initialized")
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    # 获取服务器列表
    if active_only:
        servers = server_manager.get_active_servers()
    elif type:
        try:
            server_type = ServerType(type)
            servers = server_manager.get_servers_by_type(server_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid server type: {type}")
    elif status:
        try:
            server_status = ServerStatus(status)
            servers = server_manager.get_servers_by_status(server_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid server status: {status}")
    else:
        servers = server_manager.get_all_servers()
    
    # 如果需要包含工具数量统计
    if include_tools_count and tool_manager:
        all_tools = tool_manager.get_all_tools()
        servers_with_tools = []
        
        for server in servers:
            server_dict = server.dict()
            # 计算该服务器的工具数量
            tools_count = len([
                tool for tool in all_tools 
                if tool.config.get("server_id") == server.id
            ])
            server_dict["tools_count"] = tools_count
            servers_with_tools.append(server_dict)
        
        return {
            "servers": servers_with_tools,
            "total_count": len(servers),
            "stats": server_manager.get_server_stats()
        }
    else:
        return {
            "servers": [server.dict() for server in servers],
            "total_count": len(servers),
            "stats": server_manager.get_server_stats()
        }

@router.get("/{server_id}")
async def get_server(server_id: str) -> MCPServer:
    """获取特定MCP服务器"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    server = server_manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    return server

@router.post("/{server_id}/tools/{tool_name}/call")
async def call_server_tool(
    server_id: str,
    tool_name: str,
    request_data: Dict[str, Any] = Body(...)
):
    """调用服务器的特定工具"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"调用工具: server={server_id}, tool={tool_name}, args={request_data}")
    
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    # 检查是否是PostgreSQL服务器
    if server_id == "postgres-server":
        if not server_manager.postgres_server:
            raise HTTPException(status_code=503, detail="PostgreSQL server not initialized")
        
        try:
            # 获取参数
            arguments = request_data.get("arguments", {})
            
            # 执行工具
            result = await server_manager.execute_postgres_tool(tool_name, arguments)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Tool execution failed: {str(e)}"
            )
    else:
        # 其他服务器的工具调用
        raise HTTPException(
            status_code=501,
            detail=f"Tool execution not implemented for server type: {server_id}"
        )

@router.get("/{server_id}/tools")
async def get_server_tools(server_id: str) -> List[ToolDefinition]:
    """获取特定MCP服务器的工具列表"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"开始获取服务器 {server_id} 的工具列表")
    
    if not server_manager:
        logger.error("Server manager not initialized")
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    if not tool_manager:
        logger.error("Tool manager not initialized")
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    # 检查服务器是否存在
    server = server_manager.get_server(server_id)
    if not server:
        logger.error(f"Server {server_id} not found")
        raise HTTPException(status_code=404, detail="Server not found")
    
    logger.info(f"找到服务器: {server.id}, 类型: {server.type}, 状态: {server.status}")
    
    # 获取该服务器的所有工具
    all_tools = tool_manager.get_all_tools()
    logger.info(f"工具管理器中共有 {len(all_tools)} 个工具")
    
    # 打印所有工具的信息，帮助调试
    for i, tool in enumerate(all_tools):
        tool_config = tool.config or {}
        tool_server_id = tool_config.get("server_id", "NO_SERVER_ID")
        logger.info(f"工具 {i+1}: ID={tool.id}, 名称={tool.name}, 服务器ID={tool_server_id}")
    
    # 筛选该服务器的工具
    server_tools = []
    for tool in all_tools:
        tool_config = tool.config or {}
        tool_server_id = tool_config.get("server_id")
        if tool_server_id == server_id:
            server_tools.append(tool)
            logger.info(f"匹配到工具: {tool.id} (服务器ID: {tool_server_id})")
        else:
            logger.debug(f"工具 {tool.id} 不匹配: 期望={server_id}, 实际={tool_server_id}")
    
    logger.info(f"服务器 {server_id} 共有 {len(server_tools)} 个工具")
    
    # 如果没有找到工具，记录可能的原因
    if not server_tools:
        logger.warning(f"服务器 {server_id} 没有找到工具，可能的原因:")
        logger.warning("1. 工具没有正确注册到该服务器")
        logger.warning("2. 工具的 config.server_id 字段不正确")
        logger.warning("3. 工具管理器中的工具数据有问题")
        
        # 检查是否有工具配置了错误的服务器ID
        misconfigured_tools = [
            tool for tool in all_tools 
            if tool.config and tool.config.get("server_id") and tool.config.get("server_id") != server_id
        ]
        if misconfigured_tools:
            logger.info(f"发现 {len(misconfigured_tools)} 个工具配置了其他服务器ID")
            for tool in misconfigured_tools:
                logger.info(f"  - {tool.id}: 配置的服务器ID = {tool.config.get('server_id')}")
    
    return server_tools

@router.put("/{server_id}")
async def update_server(server_id: str, updates: Dict[str, Any] = Body(...)):
    """更新MCP服务器"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    success = server_manager.update_server(server_id, updates)
    if success:
        return {"message": "Server updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="Server not found or update failed")

@router.delete("/{server_id}")
async def remove_server(server_id: str):
    """删除MCP服务器"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    success = server_manager.remove_server(server_id)
    if success:
        return {"message": "Server removed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Server not found")

@router.post("/{server_id}/enable")
async def enable_server(server_id: str):
    """启用MCP服务器"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    success = server_manager.enable_server(server_id)
    if success:
        return {"message": "Server enabled successfully"}
    else:
        raise HTTPException(status_code=404, detail="Server not found")

@router.post("/{server_id}/disable")
async def disable_server(server_id: str):
    """禁用MCP服务器"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    success = server_manager.disable_server(server_id)
    if success:
        return {"message": "Server disabled successfully"}
    else:
        raise HTTPException(status_code=404, detail="Server not found")

@router.post("/{server_id}/test")
async def test_server_connection(server_id: str):
    """测试MCP服务器连接"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    try:
        success = await server_manager.test_server_connection(server_id)
        if success:
            return {"message": "Server connection test successful", "connected": True}
        else:
            return {"message": "Server connection test failed", "connected": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.get("/stats/summary")
async def get_server_stats() -> Dict[str, Any]:
    """获取服务器统计信息"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    return server_manager.get_server_stats()

@router.post("/discover-tools")
async def discover_tools_from_all_servers():
    """从所有活跃服务器重新发现工具"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    try:
        await tool_manager.discover_tools_from_servers()
        discovered_tools = [tool for tool in tool_manager.get_all_tools() 
                          if "discovered" in tool.tags]
        return {
            "message": "Tools discovery completed for all servers",
            "discovered_count": len(discovered_tools),
            "servers_with_tools": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover tools: {str(e)}")

@router.post("/reload")
async def reload_servers_config():
    """重新加载服务器配置文件"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    try:
        # 重新加载配置
        server_manager.load_servers_from_config()
        return {
            "message": "Servers configuration reloaded successfully",
            "servers_count": len(server_manager.get_all_servers())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")

@router.get("/export")
async def export_servers_config() -> Dict[str, Any]:
    """导出服务器配置"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    return {
        "servers": {server.id: server.dict() for server in server_manager.get_all_servers()},
        "stats": server_manager.get_server_stats()
    }

@router.post("/import")
async def import_servers_config(config_data: Dict[str, Any] = Body(...)):
    """导入服务器配置"""
    if not server_manager:
        raise HTTPException(status_code=500, detail="Server manager not initialized")
    
    try:
        servers_data = config_data.get("servers", {})
        imported_count = 0
        errors = []
        
        for server_id, server_data in servers_data.items():
            try:
                server_data["id"] = server_id
                server = MCPServer(**server_data)
                if server_manager.add_server(server):
                    imported_count += 1
                else:
                    errors.append(f"Failed to add server {server_id}: already exists")
            except Exception as e:
                errors.append(f"Failed to import server {server_id}: {str(e)}")
        
        return {
            "message": f"Configuration imported successfully",
            "imported_count": imported_count,
            "total_servers": len(servers_data),
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import configuration: {str(e)}")
