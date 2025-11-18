from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from service import ResearchService, ServiceConfig
from service.dr_g import serialize_event  # 导入序列化函数

# 创建路由实例
router = APIRouter(prefix="/research", tags=["research"])

# 请求模型
class ResearchRequest(BaseModel):
    """深度研究请求模型"""
    query: str
    max_iterations: Optional[int] = 3
    
    class Config:
        schema_extra = {
            "example": {
                "query": "中国安责险的市场现状和未来发展趋势是什么？请提供具体数据支持。",
                "max_iterations": 3
            }
        }

# 获取服务实例
def get_research_service():
    """获取研究服务实例"""
    config = ServiceConfig.get_api_config()
    research_service = ResearchService(
        search_api_key=config.get('bochaai_api_key'),
        llm_api_key=config.get('dashscope_api_key'),
        llm_base_url=config.get('dashscope_base_url')
    )
    return {"research_service": research_service}

@router.post("/stream", status_code=HTTP_200_OK)
async def stream_research(
    request: ResearchRequest,
    services: Dict[str, Any] = Depends(get_research_service)
):
    """
    深度研究接口 - 流式输出
    
    对用户的研究问题执行全面的深度研究，包括问题分解、网络搜索、信息整合、数据分析和报告生成。
    使用 Server-Sent Events (SSE) 格式流式返回整个研究过程和结果。
    
    Args:
        request: 包含研究问题和配置的请求体
        
    Returns:
        流式响应，包含研究过程和结果的 SSE 格式数据
    """
    research_service = services["research_service"]
    
    async def generate_sse():
        try:
            async for event in research_service.research_stream(
                query=request.query,
                max_iterations=request.max_iterations
            ):
                # 将事件转换为 SSE 格式
                yield f"data: {event}\n\n"
        except Exception as e:
            # 使用serialize_event进行错误处理，确保JSON格式正确
            error_event = serialize_event({"type": "error", "content": str(e)})
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream"
    )

@router.get("/stream", status_code=HTTP_200_OK)
async def stream_research_get(
    query: str = Query(..., description="研究问题", example="中国安责险的市场现状和未来发展趋势是什么？"),
    max_iterations: int = Query(3, description="最大迭代次数", ge=1, le=5),
    services: Dict[str, Any] = Depends(get_research_service)
):
    """
    深度研究接口 - GET方式流式输出
    
    对用户的研究问题执行全面的深度研究，包括问题分解、网络搜索、信息整合、数据分析和报告生成。
    使用 Server-Sent Events (SSE) 格式流式返回整个研究过程和结果。
    
    Args:
        query: 研究问题
        max_iterations: 最大迭代次数（范围：1-5）
        
    Returns:
        流式响应，包含研究过程和结果的 SSE 格式数据
    """
    research_service = services["research_service"]
    
    async def generate_sse():
        try:
            async for event in research_service.research_stream(
                query=query,
                max_iterations=max_iterations
            ):
                # 将事件转换为 SSE 格式
                yield f"data: {event}\n\n"
        except Exception as e:
            # 使用serialize_event进行错误处理，确保JSON格式正确
            error_event = serialize_event({"type": "error", "content": str(e)})
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream"
    ) 