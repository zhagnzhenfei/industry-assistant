from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
import os
import logging

from service import DocumentManagementService, WebSearchService, SessionService, ServiceConfig
from service.chat_service import UnifiedChatService
from schemas import ChatRequest, SessionRequest, SessionResponse

# 记忆功能支持
try:
    from services.memory.decorators import chat_memory
    MEMORY_ENABLED = True
except ImportError:
    def chat_memory(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    MEMORY_ENABLED = False

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(prefix="/chat", tags=["chat"])

# Get unified service instances
def get_unified_services():
    """获取统一的聊天服务实例"""
    config = ServiceConfig.get_api_config()
    doc_service = DocumentManagementService()
    web_service = WebSearchService(api_key=config.get('serper_api_key'))
    session_service = SessionService()
    chat_service = UnifiedChatService(doc_service, web_service, session_service)

    return {
        "chat_service": chat_service,
        "session_service": session_service
    }

@router.post("/session", response_model=SessionResponse, status_code=HTTP_200_OK)
async def create_session(
    services: Dict[str, Any] = Depends(get_unified_services)
):
    """
    创建新的聊天会话

    Returns:
        新创建的会话信息
    """
    session_service = services["session_service"]

    try:
        session_data = session_service.create_session()
        logger.info(f"创建聊天会话成功: {session_data.get('session_id')}")
        return SessionResponse(**session_data)
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )

@router.post("/completion", status_code=HTTP_200_OK)
@chat_memory(
    memory_mode_param="memory_mode",
    user_context_param="enhanced_context",
    auto_save=True
)
async def chat_completion(
    request: ChatRequest,
    services: Dict[str, Any] = Depends(get_unified_services),
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """
    统一聊天补全接口 - 使用Milvus向量检索

    功能特性：
    - 基于Milvus的向量检索
    - Web搜索集成
    - 记忆功能支持
    - 流式响应生成

    Args:
        request: 包含用户问题和配置的请求体
        enhanced_context: 记忆增强上下文（由装饰器注入）

    Returns:
        流式响应，包含检索内容和AI生成内容
    """
    chat_service = services["chat_service"]
    session_service = services["session_service"]

    try:
        # 验证会话ID（如果提供）
        if request.session_id:
            session = session_service.get_session(request.session_id)
            if not session:
                # 如果会话不存在，创建新会话
                session_data = session_service.create_session()
                request.session_id = session_data["session_id"]
        else:
            # 创建新会话
            session_data = session_service.create_session()
            request.session_id = session_data["session_id"]

        # 增强用户问题
        enhanced_question = request.question
        if enhanced_context and enhanced_context.get("has_memories"):
            memory_context = enhanced_context.get("memory_context", "")
            memory_count = enhanced_context.get("memory_count", 0)

            if memory_context and memory_count > 0:
                enhanced_question = f"""
=== 历史对话记忆 ({memory_count}条相关记忆) ===
{memory_context}

=== 当前问题 ===
{request.question}

请基于以上历史记忆和检索到的文档，提供更加个性化和连贯的回答。
"""
                logger.info(f"🧠 [CHAT_MEMORY] 使用 {memory_count} 条历史记忆增强问题")

        logger.info(f"开始处理聊天请求: session_id={request.session_id}, question={request.question[:100]}...")

        # 创建异步生成器函数
        async def generate_response():
            try:
                # 发送开始事件（包含记忆信息）
                import json
                start_data = {
                    'type': 'start',
                    'message': '开始处理请求...',
                    'memory_enhanced': enhanced_context is not None and enhanced_context.get("has_memories", False),
                    'memory_count': enhanced_context.get("memory_count", 0) if enhanced_context else 0,
                    'session_id': request.session_id
                }
                yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"

                # 从Milvus检索文档
                milvus_docs = []
                if request.search_knowledge:
                    milvus_docs = chat_service.retrieve_from_milvus(
                        question=enhanced_question,
                        top_k=10
                    )
                    logger.info(f"从Milvus检索到 {len(milvus_docs)} 个文档")

                # 从Web搜索检索信息
                web_docs = []
                if request.search_web:
                    web_docs = chat_service.retrieve_from_web(
                        question=enhanced_question,
                        num_results=5
                    )
                    logger.info(f"从Web搜索到 {len(web_docs)} 个结果")

                # 合并文档并重排
                all_docs = milvus_docs + web_docs
                reranked_docs = chat_service.rerank_documents(
                    question=enhanced_question,
                    documents=all_docs,
                    top_n=15
                )

                # 发送检索结果信息
                retrieval_info = {
                    'type': 'retrieval_info',
                    'milvus_count': len(milvus_docs),
                    'web_count': len(web_docs),
                    'total_count': len(reranked_docs),
                    'retrieval_sources': [doc.get('source', 'unknown') for doc in reranked_docs[:5]]
                }
                yield f"data: {json.dumps(retrieval_info, ensure_ascii=False)}\n\n"

                # 生成流式回答
                for message_chunk in chat_service.get_chat_completion(
                    session_id=request.session_id,
                    question=enhanced_question,
                    retrieved_content=reranked_docs
                ):
                    yield message_chunk

            except Exception as e:
                logger.error(f"聊天处理失败: {e}")
                import json
                error_data = {
                    'type': 'error',
                    'message': f'处理失败: {str(e)}',
                    'error': str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        # 返回流式响应
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Chat-Version": "unified-milvus-v1"
            }
        )

    except Exception as e:
        logger.error(f"聊天补全接口错误: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天补全失败: {str(e)}"
        )

@router.get("/health", status_code=HTTP_200_OK)
async def health_check():
    """
    聊天服务健康检查
    """
    return {
        "status": "healthy",
        "service": "Unified Chat Service",
        "version": "unified-milvus-v1",
        "memory_enabled": MEMORY_ENABLED,
        "milvus_enabled": True
    }
