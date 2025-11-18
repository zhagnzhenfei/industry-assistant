#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体聊天相关的数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatSessionCreateRequest(BaseModel):
    """创建聊天会话请求"""
    assistant_id: str = Field(..., description="智能体ID")
    title: Optional[str] = Field(None, description="会话标题", min_length=1, max_length=200)


class ChatSessionResponse(BaseModel):
    """聊天会话响应"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    assistant_id: str = Field(..., description="智能体ID")
    title: str = Field(..., description="会话标题")
    status: str = Field(..., description="会话状态")
    created_at: int = Field(..., description="创建时间戳")
    updated_at: int = Field(..., description="更新时间戳")


class ChatSessionListResponse(BaseModel):
    """聊天会话列表响应"""
    sessions: List[ChatSessionResponse] = Field(..., description="会话列表")
    total_count: int = Field(..., description="总数量")


class ChatMessageRequest(BaseModel):
    """发送聊天消息请求"""
    session_id: str = Field(..., description="会话ID")
    content: str = Field(..., description="消息内容", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外信息")


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    message_id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外信息")
    created_at: int = Field(..., description="创建时间戳")


class ChatHistoryResponse(BaseModel):
    """聊天历史响应"""
    session: ChatSessionResponse = Field(..., description="会话信息")
    messages: List[ChatMessageResponse] = Field(..., description="消息列表")
    total_messages: int = Field(..., description="消息总数")


class ChatCompletionRequest(BaseModel):
    """聊天补全请求"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="用户消息内容", min_length=1)


class ChatCompletionResponse(BaseModel):
    """聊天补全响应"""
    session_id: str = Field(..., description="会话ID")
    user_message: ChatMessageResponse = Field(..., description="用户消息")
    assistant_message: ChatMessageResponse = Field(..., description="智能体回复")
    created_at: int = Field(..., description="创建时间戳")


class ChatSessionUpdateRequest(BaseModel):
    """更新聊天会话请求"""
    title: Optional[str] = Field(None, description="会话标题", min_length=1, max_length=200)
    status: Optional[str] = Field(None, description="会话状态")


class ChatSessionDeleteResponse(BaseModel):
    """删除聊天会话响应"""
    message: str = Field(..., description="操作结果")
    deleted_count: int = Field(..., description="删除的消息数量") 