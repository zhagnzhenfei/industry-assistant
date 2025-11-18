from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from typing import List

from schemas import WebSearchRequest, WebSearchResponse

# Create router instance
router = APIRouter(prefix="/search", tags=["search"])

# Get Web Search Service instance
def get_web_search_service():
    """获取Web搜索服务实例"""
    from service.web_search_service import WebSearchService
    return WebSearchService()

@router.post("/web", status_code=HTTP_200_OK, response_model=WebSearchResponse)
async def web_search(
    request: WebSearchRequest,
    search_service = Depends(get_web_search_service)
):
    """
    执行Web搜索，返回搜索结果。
    现在使用MCP协议进行搜索。
    
    Args:
        request: 包含搜索参数的请求体
        
    Returns:
        搜索结果响应
    """
    try:
        # 调用MCP搜索服务
        search_results = await search_service.search(
            query=request.query,
            engine="serper",  # 默认使用serper引擎
            gl=request.gl,
            hl=request.hl,
            autocorrect=request.autocorrect,
            page=request.page,
            search_type=request.search_type
        )
        
        # 检查是否有错误
        if not search_results.get("success", False):
            return {
                "success": False,
                "message": search_results.get("message", "Search failed"),
                "query": request.query,
                "results": []
            }
        
        # 提取并格式化搜索结果（保持兼容性）
        formatted_results = search_service.extract_search_results(search_results)
        
        # 构建响应
        return {
            "success": True,
            "query": request.query,
            "results": formatted_results,
            "raw_results": search_results.get("raw_results", {})
        }
        
    except Exception as e:
        # 处理异常
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing MCP web search: {str(e)}"
        )

@router.post("/web/multi-engine", status_code=HTTP_200_OK)
async def web_search_multi_engine(
    request: WebSearchRequest,
    engines: List[str] = ["serper"],
    max_results_per_engine: int = 5,
    search_service = Depends(get_web_search_service)
):
    """
    使用多个搜索引擎进行搜索（新功能）
    
    Args:
        request: 包含搜索参数的请求体
        engines: 要使用的搜索引擎列表
        max_results_per_engine: 每个引擎返回的最大结果数
        
    Returns:
        多引擎搜索结果
    """
    try:
        # 调用多引擎搜索
        search_results = await search_service.search_with_multiple_engines(
            query=request.query,
            engines=engines,
            max_results_per_engine=max_results_per_engine
        )
        
        return search_results
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing multi-engine search: {str(e)}"
        )

@router.get("/engines", status_code=HTTP_200_OK)
async def list_search_engines(
    search_service = Depends(get_web_search_service)
):
    """
    列出所有可用的搜索引擎
    
    Returns:
        可用搜索引擎列表
    """
    try:
        engines = await search_service.list_search_engines()
        return engines
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing search engines: {str(e)}"
        )

@router.get("/mcp/tools", status_code=HTTP_200_OK)
async def list_mcp_tools():
    """
    列出所有MCP工具（管理接口）
    
    Returns:
        所有可用的MCP工具
    """
    try:
        from service.mcp_api_service import MCPAPIService
        mcp_service = MCPAPIService()
        servers = await mcp_service.get_mcp_servers()
        return {
            "success": True,
            "servers": servers
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing MCP tools: {str(e)}"
        )

@router.get("/mcp/servers/{server_name}/info", status_code=HTTP_200_OK)
async def get_mcp_server_info(server_name: str):
    """
    获取指定MCP服务器的信息
    
    Args:
        server_name: 服务器名称
        
    Returns:
        服务器详细信息
    """
    try:
        from service.mcp_api_service import MCPAPIService
        mcp_service = MCPAPIService()
        info = await mcp_service.get_server_info(server_name)
        return {
            "success": True,
            "server_name": server_name,
            "info": info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting server info: {str(e)}"
        ) 