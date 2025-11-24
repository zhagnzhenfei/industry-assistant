#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体聊天路由
提供智能体与用户的对话功能
支持记忆增强功能
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from schemas.chat import (
    ChatSessionCreateRequest, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse,
    ChatCompletionRequest, ChatCompletionResponse,
    ChatSessionUpdateRequest, ChatSessionDeleteResponse
)
from service.assistant_chat_service import AssistantChatService
from service.auth_service import get_current_user
from utils.database import default_manager

# 记忆功能支持
try:
    from services.memory.decorators import chat_memory
    MEMORY_ENABLED = True
except ImportError:
    # 如果记忆模块不可用，使用空装饰器
    def chat_memory(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    MEMORY_ENABLED = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant-chat", tags=["assistant-chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建新的聊天会话"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            # 如果title为空，提供默认值
            title = request.title or f"默认话题"
            session_data = chat_service.create_chat_session(
                db=db_session,
                user_id=user_id,
                assistant_id=request.assistant_id,
                title=title
            )
            
            logger.info(f"用户 {user_id} 创建聊天会话成功: {session_data['session_id']}")
            return ChatSessionResponse(**session_data)
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"创建聊天会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"创建聊天会话失败: {str(e)}")


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    assistant_id: Optional[str] = Query(None, description="智能体ID"),
    status: str = Query("active", description="会话状态"),
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户的聊天会话列表"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            sessions = chat_service.get_user_sessions(
                db=db_session,
                user_id=user_id,
                assistant_id=assistant_id,
                status=status,
                limit=limit,
                offset=offset
            )
            
            logger.info(f"用户 {user_id} 获取会话列表成功: {len(sessions)} 个会话")
            return ChatSessionListResponse(sessions=sessions, total_count=len(sessions))
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=400, detail=f"获取会话列表失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取特定聊天会话信息"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            session_data = chat_service.get_session_by_id(
                db=db_session,
                session_id=session_id,
                user_id=user_id
            )
            
            if not session_data:
                raise HTTPException(status_code=404, detail="会话不存在或无权限访问")
            
            logger.info(f"用户 {user_id} 获取会话信息成功: {session_id}")
            return ChatSessionResponse(**session_data)
            
        finally:
            db_session.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        raise HTTPException(status_code=400, detail=f"获取会话信息失败: {str(e)}")


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    request: ChatSessionUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """更新聊天会话信息"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            
            # 构建更新字段
            updates = {}
            if request.title is not None:
                updates["title"] = request.title
            if request.status is not None:
                updates["status"] = request.status
            
            success = chat_service.update_session(
                db=db_session,
                session_id=session_id,
                user_id=user_id,
                updates=updates
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="会话不存在或无权限访问")
            
            # 获取更新后的会话信息
            session_data = chat_service.get_session_by_id(
                db=db_session,
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"用户 {user_id} 更新会话成功: {session_id}")
            return ChatSessionResponse(**session_data)
            
        finally:
            db_session.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"更新会话失败: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=ChatSessionDeleteResponse)
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除聊天会话"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            result = chat_service.delete_session(
                db=db_session,
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"用户 {user_id} 删除会话成功: {session_id}")
            return ChatSessionDeleteResponse(**result)
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"删除会话失败: {str(e)}")


@router.post("/sessions/{session_id}/archive")
async def archive_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """归档聊天会话"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            success = chat_service.archive_session(
                db=db_session,
                session_id=session_id,
                user_id=user_id
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="会话不存在或无权限访问")
            
            logger.info(f"用户 {user_id} 归档会话成功: {session_id}")
            return {"message": "会话归档成功"}
            
        finally:
            db_session.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"归档会话失败: {e}")
        raise HTTPException(status_code=400, detail=f"归档会话失败: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = Query(100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    current_user: dict = Depends(get_current_user)
):
    """获取会话的消息历史"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            messages = chat_service.get_session_messages(
                db=db_session,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                offset=offset
            )
            
            logger.info(f"用户 {user_id} 获取会话消息成功: {session_id}, {len(messages)} 条消息")
            return [ChatMessageResponse(**msg) for msg in messages]
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(status_code=400, detail=f"获取会话消息失败: {str(e)}")


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取完整的聊天历史"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            history = chat_service.get_chat_history(
                db=db_session,
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"用户 {user_id} 获取聊天历史成功: {session_id}")
            return ChatHistoryResponse(**history)
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        raise HTTPException(status_code=400, detail=f"获取聊天历史失败: {str(e)}")


@router.post("/completion", response_model=ChatCompletionResponse)
@chat_memory(
    memory_mode_param="memory_mode",
    user_context_param="enhanced_context",
    auto_save=True
)
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: dict = Depends(get_current_user),
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """智能体聊天补全 - 支持记忆功能"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)

        # 直接创建数据库会话
        db_session = default_manager.session_factory()

        try:
            chat_service = AssistantChatService()

            # 增强用户消息内容
            enhanced_message = request.message
            if enhanced_context and enhanced_context.get("has_memories"):
                # 构建记忆增强的消息
                memory_context = enhanced_context.get("memory_context", "")
                memory_count = enhanced_context.get("memory_count", 0)

                if memory_context and memory_count > 0:
                    enhanced_message = f"""
=== 历史对话记忆 ({memory_count}条相关记忆) ===
{memory_context}

=== 当前对话 ===
{request.message}

请基于以上历史记忆，提供更加个性化和连贯的回复。
"""

                    logger.info(f"🧠 [CHAT_MEMORY] 用户 {user_id} 使用 {memory_count} 条历史记忆进行对话增强")

            # 处理用户消息
            result = await chat_service.process_user_message(
                db=db_session,
                session_id=request.session_id,
                user_id=user_id,
                message_content=enhanced_message,
                # 传递记忆上下文给服务层（可选）
                enhanced_context=enhanced_context if enhanced_context and enhanced_context.get("has_memories") else None
            )

            # 在响应中添加记忆信息
            if enhanced_context and enhanced_context.get("has_memories"):
                if isinstance(result, dict):
                    result["memory_enhanced"] = True
                    result["memory_count"] = enhanced_context.get("memory_count", 0)

            logger.info(f"用户 {user_id} 聊天补全成功: {request.session_id}")
            return ChatCompletionResponse(**result)

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"聊天补全失败: {e}")
        raise HTTPException(status_code=400, detail=f"聊天补全失败: {str(e)}")


@router.post("/completion/stream")
@chat_memory(
    memory_mode_param="memory_mode",
    user_context_param="enhanced_context",
    auto_save=True
)
async def chat_completion_stream(
    request: ChatCompletionRequest,
    current_user: dict = Depends(get_current_user),
    enhanced_context: Optional[Dict[str, Any]] = None
):
    """智能体聊天补全 - 流式输出（支持记忆功能）"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)

        # 直接创建数据库会话
        db_session = default_manager.session_factory()

        try:
            chat_service = AssistantChatService()

            # 增强用户消息内容
            enhanced_message = request.message
            if enhanced_context and enhanced_context.get("has_memories"):
                # 构建记忆增强的消息
                memory_context = enhanced_context.get("memory_context", "")
                memory_count = enhanced_context.get("memory_count", 0)

                if memory_context and memory_count > 0:
                    enhanced_message = f"""
=== 历史对话记忆 ({memory_count}条相关记忆) ===
{memory_context}

=== 当前对话 ===
{request.message}

请基于以上历史记忆，提供更加个性化和连贯的回复。
"""

                    logger.info(f"🧠 [CHAT_MEMORY_STREAM] 用户 {user_id} 使用 {memory_count} 条历史记忆进行流式对话增强")

            # 设置SSE响应头
            from fastapi.responses import StreamingResponse
            import json

            async def generate_stream():
                try:
                    # 发送开始事件（包含记忆信息）
                    start_data = {
                        'type': 'start',
                        'message': '开始处理请求...',
                        'memory_enhanced': enhanced_context is not None and enhanced_context.get("has_memories", False),
                        'memory_count': enhanced_context.get("memory_count", 0) if enhanced_context else 0
                    }
                    yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"

                    # 处理用户消息并生成流式响应
                    async for chunk in chat_service.process_user_message_stream(
                        db=db_session,
                        session_id=request.session_id,
                        user_id=user_id,
                        message_content=enhanced_message,
                        # 传递记忆上下文给服务层（可选）
                        enhanced_context=enhanced_context if enhanced_context and enhanced_context.get("has_memories") else None
                    ):
                        # 在流式响应中添加记忆信息
                        if enhanced_context and enhanced_context.get("has_memories"):
                            if isinstance(chunk, dict):
                                chunk["memory_enhanced"] = True
                                chunk["memory_count"] = enhanced_context.get("memory_count", 0)

                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                    # 发送结束事件
                    end_data = {
                        'type': 'end',
                        'message': '请求处理完成',
                        'memory_saved': enhanced_context is not None and enhanced_context.get("has_memories", False)
                    }
                    yield f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"

                except Exception as e:
                    error_chunk = {
                        'type': 'error',
                        'message': f'处理失败: {str(e)}',
                        'error': str(e)
                    }
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                    "X-Chat-Version": "v2-memory-enhanced"
                }
            )

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"流式聊天补全失败: {e}")
        raise HTTPException(status_code=400, detail=f"流式聊天补全失败: {str(e)}")


@router.post("/sessions/{session_id}/send", response_model=ChatMessageResponse)
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """发送消息到会话"""
    try:
        # 从ORM对象中提取user_id
        user_id = current_user.user_id if hasattr(current_user, 'user_id') else str(current_user.user_id)
        
        # 直接创建数据库会话
        db_session = default_manager.session_factory()
        
        try:
            chat_service = AssistantChatService()
            message_data = chat_service.add_message(
                db=db_session,
                session_id=session_id,
                role="user",
                content=request.content,
                metadata=request.metadata
            )
            
            logger.info(f"用户 {user_id} 发送消息成功: {session_id}")
            return ChatMessageResponse(**message_data)
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=400, detail=f"发送消息失败: {str(e)}")
