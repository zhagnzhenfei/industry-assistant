from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from service import ResearchService, ServiceConfig
from service.dr_g import serialize_event  # 导入序列化函数

# 记忆功能支持（新增）
try:
    from services.memory.decorators import research_memory
    from service.auth_service import get_current_user
    from models.user_models import User
    MEMORY_ENABLED = True
except ImportError:
    # 如果记忆模块不可用，使用空装饰器
    def research_memory(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    MEMORY_ENABLED = False

# 创建路由实例
router = APIRouter(prefix="/research", tags=["research"])

# 请求模型
class ResearchRequest(BaseModel):
    """深度研究请求模型"""
    query: str
    max_iterations: Optional[int] = 3
    memory_mode: Optional[str] = "smart"  # 新增记忆模式支持

    class Config:
        schema_extra = {
            "example": {
                "query": "中国安责险的市场现状和未来发展趋势是什么？请提供具体数据支持。",
                "max_iterations": 3,
                "memory_mode": "smart"
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


@router.post("/stream-with-memory", status_code=HTTP_200_OK)
@research_memory(
    memory_mode_param="memory_mode",
    user_context_param="enhanced_context",
    auto_save=True
)
async def stream_research_with_memory(
    request: ResearchRequest,
    services: Dict[str, Any] = Depends(get_research_service),
    current_user: User = Depends(get_current_user) if MEMORY_ENABLED else None,
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """
    深度研究接口 - 支持记忆功能的流式输出

    在原有研究功能基础上，增加了记忆支持：
    - 自动加载用户相关的研究历史
    - 基于历史记忆提供更相关的研究结果
    - 自动保存新的研究成果到记忆中

    Args:
        request: 包含研究问题、配置和记忆模式的请求体
        current_user: 当前认证用户
        enhanced_context: 增强的上下文（由记忆装饰器注入）

    Returns:
        流式响应，包含研究过程和结果的 SSE 格式数据
    """
    research_service = services["research_service"]

    # 使用增强的查询（如果有的话）
    query = request.query
    if enhanced_context and enhanced_context.get("has_memories"):
        # 可以基于历史记忆调整查询
        memory_context = enhanced_context.get("memory_context", "")
        if memory_context:
            # 这里可以实现更复杂的查询增强逻辑
            # 目前只是记录日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🧠 [RESEARCH_WITH_MEMORY] 使用 {enhanced_context.get('memory_count', 0)} 条历史记忆")

    async def generate_sse():
        try:
            # 生成研究ID用于记忆保存
            import datetime
            research_id = f"research_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(query) % 10000}"

            async for event in research_service.research_stream(
                query=query,
                max_iterations=request.max_iterations
            ):
                # 添加记忆信息到事件中
                if enhanced_context and enhanced_context.get("has_memories"):
                    try:
                        import json
                        event_dict = json.loads(event)
                        event_dict["memory_info"] = {
                            "enabled": True,
                            "count": enhanced_context.get("memory_count", 0),
                            "research_id": research_id
                        }
                        event = json.dumps(event_dict, ensure_ascii=False)
                    except:
                        # 如果解析失败，使用原事件
                        pass

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