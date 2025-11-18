"""
工具管理API
"""
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, List, Optional, Any
from app.models.tool_models import (
    ToolDefinition, ToolExecutionRequest, ToolExecutionResult
)
from app.services.tool_manager import ToolManager
from app.services.execution_service import ToolExecutionService

router = APIRouter()

# 依赖注入
tool_manager: Optional[ToolManager] = None
execution_service: Optional[ToolExecutionService] = None

@router.post("")
async def add_tool(tool: ToolDefinition):
    """添加工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    success = tool_manager.add_tool(tool)
    if success:
        return {"message": "Tool added successfully", "tool_id": tool.id}
    else:
        raise HTTPException(status_code=500, detail="Failed to add tool")

@router.get("")
async def list_tools(
    category: Optional[str] = Query(None, description="工具分类"),
    tag: Optional[str] = Query(None, description="工具标签"),
    status: Optional[str] = Query(None, description="工具状态"),
    search: Optional[str] = Query(None, description="搜索关键词")
) -> List[ToolDefinition]:
    """列出工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    if search:
        return tool_manager.search_tools(search)
    elif category:
        return tool_manager.get_tools_by_category(category)
    elif tag:
        return tool_manager.get_tools_by_tag(tag)
    elif status:
        if status == "active":
            return tool_manager.get_active_tools()
        else:
            return [tool for tool in tool_manager.get_all_tools() if tool.status.value == status]
    else:
        return tool_manager.get_all_tools()

@router.get("/{tool_id}")
async def get_tool(tool_id: str) -> ToolDefinition:
    """获取特定工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    tool = tool_manager.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return tool

@router.put("/{tool_id}")
async def update_tool(tool_id: str, updates: Dict[str, Any] = Body(...)):
    """更新工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    success = tool_manager.update_tool(tool_id, updates)
    if success:
        return {"message": "Tool updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update tool")

@router.delete("/{tool_id}")
async def remove_tool(tool_id: str):
    """删除工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    success = tool_manager.remove_tool(tool_id)
    if success:
        return {"message": "Tool removed successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove tool")

@router.post("/{tool_id}/enable")
async def enable_tool(tool_id: str):
    """启用工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    success = tool_manager.enable_tool(tool_id)
    if success:
        return {"message": "Tool enabled successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to enable tool")

@router.post("/{tool_id}/disable")
async def disable_tool(tool_id: str):
    """禁用工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")
    
    success = tool_manager.disable_tool(tool_id)
    if success:
        return {"message": "Tool disabled successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disable tool")

@router.get("/categories/list")
async def get_tool_categories() -> List[str]:
    """获取工具分类列表"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    return tool_manager.get_tool_categories()

@router.get("/tags/list")
async def get_tool_tags() -> List[str]:
    """获取工具标签列表"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    return tool_manager.get_tool_tags()

@router.get("/statistics")
async def get_tool_statistics() -> Dict[str, Any]:
    """获取工具统计信息"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    return tool_manager.get_tool_stats()

@router.post("/config/reload")
async def reload_tools_config():
    """重新加载工具配置文件"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    success = tool_manager.reload_config()
    if success:
        return {"message": "工具配置重新加载成功"}
    else:
        raise HTTPException(status_code=500, detail="重新加载配置失败")

@router.get("/config/export")
async def export_tools_config() -> Dict[str, Any]:
    """导出工具配置"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    return tool_manager.export_config()

@router.post("/config/import")
async def import_tools_config(config_data: Dict[str, Any] = Body(...)):
    """导入工具配置"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    success = tool_manager.import_config(config_data)
    if success:
        return {"message": "工具配置导入成功"}
    else:
        raise HTTPException(status_code=500, detail="导入配置失败")

@router.post("/discover/all-servers")
async def discover_all_mcp_tools():
    """从所有MCP服务器重新发现工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    try:
        await tool_manager.discover_tools_from_servers()
        discovered_tools = [tool for tool in tool_manager.get_all_tools()
                          if "discovered" in tool.tags]
        return {
            "message": "MCP工具发现完成",
            "discovered_count": len(discovered_tools),
            "discovered_tools": [{"id": tool.id, "name": tool.name, "server": tool.config.get("server_id")}
                               for tool in discovered_tools]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP工具发现失败: {str(e)}")

@router.post("/discover/server/{server_id}")
async def discover_server_mcp_tools(server_id: str):
    """从指定MCP服务器重新发现工具"""
    if not tool_manager:
        raise HTTPException(status_code=500, detail="Tool manager not initialized")

    try:
        await tool_manager.discover_tools_from_server(server_id)
        server_tools = [tool for tool in tool_manager.get_all_tools()
                       if tool.config and tool.config.get("server_id") == server_id]
        return {
            "message": f"服务器 {server_id} 的工具发现完成",
            "server_id": server_id,
            "discovered_count": len(server_tools),
            "discovered_tools": [{"id": tool.id, "name": tool.name} for tool in server_tools]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从服务器 {server_id} 发现工具失败: {str(e)}")
