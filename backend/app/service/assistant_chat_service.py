#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体聊天服务
处理智能体与用户的对话交互
"""

import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from openai import OpenAI
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from models.chat_models import ChatSession, ChatMessage
from models.assistant_models import Assistant
from service.mcp_service_manager import MCPServiceManager
from service.core.retrieval import retrieve_content
from services.memory.memory_factory import get_memory_service


logger = logging.getLogger(__name__)


class AssistantChatService:
    """智能体聊天服务"""
    
    def __init__(self):
        self.mcp_manager = MCPServiceManager()
    
    def create_chat_session(
        self, 
        db: Session, 
        user_id: str, 
        assistant_id: str, 
        title: str
    ) -> Dict[str, Any]:
        """创建新的聊天会话"""
        try:
            # 验证智能体是否存在
            assistant = db.query(Assistant).filter(
                Assistant.assistant_id == assistant_id,
                Assistant.user_id == user_id
            ).first()
            
            if not assistant:
                raise ValueError(f"智能体 {assistant_id} 不存在或无权限访问")
            
            # 创建会话
            session = ChatSession(
                user_id=user_id,
                assistant_id=assistant_id,
                title=title,
                status='active'
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            logger.info(f"创建聊天会话成功: session_id={session.session_id}, user_id={user_id}, assistant_id={assistant_id}")
            
            return session.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建聊天会话失败: {e}")
            raise
    
    def get_user_sessions(
        self, 
        db: Session, 
        user_id: str, 
        assistant_id: Optional[str] = None,
        status: str = 'active',
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户的聊天会话列表"""
        try:
            query = db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.status == status
            )
            
            if assistant_id:
                query = query.filter(ChatSession.assistant_id == assistant_id)
            
            sessions = query.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit).all()
            
            return [session.to_dict() for session in sessions]
            
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            raise
    
    def get_session_by_id(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据ID获取会话信息"""
        try:
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if session:
                return session.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            raise
    
    def add_message(
        self, 
        db: Session, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """添加聊天消息"""
        try:
            # 验证会话是否存在
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                raise ValueError(f"会话 {session_id} 不存在")
            
            # 创建消息
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                message_metadata=metadata
            )
            
            db.add(message)
            
            # 更新会话的更新时间
            session.updated_at = int(time.time())
            
            db.commit()
            db.refresh(message)
            
            logger.info(f"添加聊天消息成功: message_id={message.message_id}, session_id={session_id}, role={role}")
            
            return message.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f"添加聊天消息失败: {e}")
            raise
    
    def get_session_messages(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取会话的消息历史"""
        try:
            # 验证会话权限
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"会话 {session_id} 不存在或无权限访问")
            
            # 获取消息
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit).all()
            
            return [message.to_dict() for message in messages]
            
        except Exception as e:
            logger.error(f"获取会话消息失败: {e}")
            raise
    
    def get_chat_history(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """获取完整的聊天历史"""
        try:
            # 获取会话信息
            session_dict = self.get_session_by_id(db, session_id, user_id)
            if not session_dict:
                raise ValueError(f"会话 {session_id} 不存在或无权限访问")
            
            # 获取消息列表
            messages = self.get_session_messages(db, session_id, user_id)
            
            return {
                "session": session_dict,
                "messages": messages,
                "total_messages": len(messages)
            }
            
        except Exception as e:
            logger.error(f"获取聊天历史失败: {e}")
            raise
    
    def update_session(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新会话信息"""
        try:
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                return False
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(session, field) and value is not None:
                    setattr(session, field, value)
            
            session.updated_at = int(time.time())
            db.commit()
            
            logger.info(f"更新会话成功: session_id={session_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新会话失败: {e}")
            return False
    
    def delete_session(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """删除会话（软删除）"""
        try:
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"会话 {session_id} 不存在或无权限访问")
            
            # 获取消息数量
            message_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).count()
            
            # 软删除会话
            session.status = 'deleted'
            session.updated_at = int(time.time())
            
            db.commit()
            
            logger.info(f"删除会话成功: session_id={session_id}, 消息数量={message_count}")
            
            return {
                "message": "会话删除成功",
                "deleted_count": message_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除会话失败: {e}")
            raise
    
    def archive_session(
        self, 
        db: Session, 
        session_id: str, 
        user_id: str
    ) -> bool:
        """归档会话"""
        try:
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                return False
            
            session.status = 'archived'
            session.updated_at = int(time.time())
            db.commit()
            
            logger.info(f"归档会话成功: session_id={session_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"归档会话失败: {e}")
            return False
    
    async def process_user_message(
        self,
        db: Session,
        session_id: str,
        user_id: str,
        message_content: str,
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """处理用户消息并生成智能体回复 - 使用标准Function Call流程"""
        try:
            # 获取会话信息
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"会话 {session_id} 不存在或无权限访问")
            
            # 获取智能体信息
            assistant = db.query(Assistant).filter(
                Assistant.assistant_id == session.assistant_id
            ).first()
            
            if not assistant:
                raise ValueError(f"智能体 {session.assistant_id} 不存在")
            
            # 添加用户消息
            user_message = self.add_message(
                db, session_id, "user", message_content
            )
            
            # 获取会话历史消息（用于构建上下文）
            message_history = await self._build_message_history(db, session_id, limit=20)
            
            # 使用标准Function Call流程处理消息
            assistant_reply = await self._process_message_with_function_calls(
                message_content, assistant, message_history
            )
            
            # 添加智能体回复
            assistant_message = self.add_message(
                db, session_id, "assistant", assistant_reply
            )
            
            logger.info(f"处理用户消息成功: session_id={session_id}, user_message_id={user_message['message_id']}, assistant_message_id={assistant_message['message_id']}")
            
            return {
                "session_id": session_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "created_at": int(time.time())
            }
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            raise

    async def process_user_message_stream(
        self,
        db: Session,
        session_id: str,
        user_id: str,
        message_content: str,
        enhanced_context: Optional[Dict[str, Any]] = None
    ):
        """处理用户消息并生成流式响应"""
        try:
            logger.info(f"开始流式处理用户消息: session_id={session_id}")
            
            # 获取会话信息
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"会话 {session_id} 不存在或无权限访问")
            
            # 获取智能体信息
            assistant = db.query(Assistant).filter(
                Assistant.assistant_id == session.assistant_id
            ).first()
            
            if not assistant:
                raise ValueError(f"智能体 {session.assistant_id} 不存在")
            
            # 获取Mem0记忆服务
            memory_service = get_memory_service()
            user_context = ""
            
            # 如果记忆服务可用，获取用户上下文记忆
            if memory_service:
                try:
                    user_context = await memory_service.get_user_context(
                        user_id=user_id,
                        query=message_content,
                        limit=5  # 获取最近5条相关记忆
                    )
                    if user_context:
                        logger.info(f"获取到用户上下文记忆，长度: {len(user_context)}")
                        yield {
                            'type': 'memory_context',
                            'context_length': len(user_context),
                            'timestamp': int(time.time())
                        }
                except Exception as e:
                    logger.warning(f"获取用户记忆上下文失败: {e}")
            
            # 添加用户消息
            user_message = self.add_message(
                db, session_id, "user", message_content
            )
            
            
            # 获取可用的MCP工具
            available_tools = await self._get_available_function_tools(assistant)
            yield {
                'type': 'tools_ready',
                'tools_count': len(available_tools),
                'timestamp': int(time.time())
            }
            
            # 构建消息列表
            messages = self._build_messages_for_llm([], message_content, assistant, available_tools, user_context)
            # yield {
            #     'type': 'messages_ready',
            #     'messages_count': len(messages),
            #     'timestamp': int(time.time())
            # }
            
            # 第一次LLM调用（非流式，用于工具判断）
            logger.info("开始第一次LLM调用判断工具需求")
            yield {
                'type': 'llm_start',
                'message': '开始调用大模型判断是否需要工具...',
                'timestamp': int(time.time())
            }
            
            response = await self._call_bailian_with_function_calls(messages, available_tools, stream=False)
            
            if response and 'choices' in response:
                choice = response["choices"][0]
                message = choice.get("message", {})
                full_content = message.get("content", "")
                tool_calls = message.get("tool_calls")
                
                yield {
                    'type': 'llm_response',
                    'message': '大模型响应完成，开始分析是否需要工具调用',
                    'timestamp': int(time.time())
                }
                
                logger.info(f"LLM调用完成，检测到工具调用: {'是' if tool_calls else '否'}")
                
                if tool_calls:
                    yield {
                        'type': 'tool_calls_detected',
                        'tools_count': len(tool_calls),
                        'message': f'检测到 {len(tool_calls)} 个工具调用',
                        'timestamp': int(time.time())
                    }
                
                # 并行执行知识库检索（如果智能体启用了知识库）
                knowledge_results = []
                if hasattr(assistant, 'enable_knowledge_base') and assistant.enable_knowledge_base:
                    yield {
                        'type': 'knowledge_retrieval_start',
                        'message': '开始知识库检索...',
                        'timestamp': int(time.time())
                    }
                    
                    try:
                        knowledge_results = await self._retrieve_knowledge_base(user_id, message_content)
                        yield {
                            'type': 'knowledge_retrieval_complete',
                            'message': f'知识库检索完成，找到 {len(knowledge_results)} 个相关文档片段',
                            'results_count': len(knowledge_results),
                            'timestamp': int(time.time())
                        }
                    except Exception as e:
                        logger.error(f"知识库检索失败: {e}")
                        yield {
                            'type': 'knowledge_retrieval_error',
                            'message': f'知识库检索失败: {str(e)}',
                            'timestamp': int(time.time())
                        }
                
                if tool_calls:
                    logger.info(f"开始执行 {len(tool_calls)} 个工具调用")
                    
                    # 执行工具调用
                    for i, tool_call in enumerate(tool_calls):
                        tool_name = tool_call.get('function', {}).get('name', 'unknown')
                        yield {
                            'type': 'tool_execution_start',
                            'tool_index': i + 1,
                            'tool_name': tool_name,
                            'message': f'开始执行工具 {tool_name}',
                            'timestamp': int(time.time())
                        }
                        
                        # Schema校验（校验1）
                        try:
                            # 验证工具调用参数
                            if not self._validate_tool_call_schema(tool_call):
                                raise ValueError(f"工具调用 {tool_name} 参数校验失败")
                        except Exception as e:
                            logger.error(f"Schema校验失败: {e}")
                            # 失败回退：将错误信息作为function结果
                            tool_result = {
                                "success": False,
                                "error": "Schema校验失败",
                                "message": str(e)
                            }
                        else:
                            # 执行工具
                            tool_result = await self._execute_function_call(tool_call, assistant)
                        
                        yield {
                            'type': 'tool_execution_result',
                            'tool_index': i + 1,
                            'tool_name': tool_name,
                            'success': tool_result.get('success', False),
                            'result': tool_result,
                            'timestamp': int(time.time())
                        }
                    
                    # 第二次LLM调用生成最终回复（流式输出给用户）
                    yield {
                        'type': 'llm_final_start',
                        'message': '工具执行完成，开始流式生成最终回复...',
                        'timestamp': int(time.time())
                    }
                    
                    # 按照规范构建第二轮消息：只追加assistant(function_call) + function结果
                    final_messages = []
                    
                    # 如果有知识库检索结果，添加知识库上下文到system消息
                    if knowledge_results:
                        knowledge_context = self._build_knowledge_context(knowledge_results)
                        final_messages.append({
                            "role": "system",
                            "content": knowledge_context
                        })
                    
                    # 不包含原始system prompt，只追加第一轮的结果
                    final_messages.append({
                        "role": "assistant",
                        "content": full_content,
                        "tool_calls": tool_calls
                    })
                    
                    for tool_call in tool_calls:
                        tool_result = await self._execute_function_call(tool_call, assistant)
                        final_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })
                    
                    # 第二次LLM调用：不传入工具信息，专注于生成回复
                    logger.info(f"开始第二次LLM调用生成最终回复，消息数量: {len(final_messages)}")
                    
                    final_response = await self._call_bailian_with_function_calls(final_messages, [], stream=True)
                    
                    if final_response and 'stream_response' in final_response:
                        final_stream_response = final_response['stream_response']
                        final_full_content = ""
                        
                        try:
                            # 使用OpenAI客户端的流式处理
                            for chunk in final_stream_response:
                                if chunk.choices[0].finish_reason == "stop":
                                    logger.info("最终回复流式响应完成")
                                    break
                                elif chunk.choices[0].finish_reason is not None:
                                    break
                                else:
                                    # 实时输出消息
                                    delta = chunk.choices[0].delta
                                    if delta.content:
                                        final_full_content += delta.content
                                        # 实时返回最终回复内容片段
                                        yield {
                                            'type': 'assistant_content_chunk',
                                            'content': delta.content,
                                            'timestamp': int(time.time())
                                        }
                                        
                        except Exception as e:
                            logger.error(f"最终回复流式响应处理异常: {e}")
                            yield {
                                'type': 'error',
                                'message': f'最终回复生成异常: {str(e)}',
                                'timestamp': int(time.time())
                            }
                            return
                        
                        # 如果没有获取到最终内容，返回错误
                        if not final_full_content:
                            logger.warning("最终回复流式响应未获取到有效内容")
                            yield {
                                'type': 'error',
                                'message': '未获取到有效的最终回复内容',
                                'timestamp': int(time.time())
                            }
                            return
                        
                        # 添加助手回复到数据库
                        assistant_message = self.add_message(
                            db, session_id, "assistant", final_full_content
                        )
                        
                        yield {
                            'type': 'assistant_message',
                            'message_id': assistant_message['message_id'],
                            'content': final_full_content,
                            'timestamp': int(time.time())
                        }
                    else:
                        logger.error("第二次LLM调用失败或响应格式异常")
                        yield {
                            'type': 'error',
                            'message': '最终回复生成失败',
                            'timestamp': int(time.time())
                        }
                else:
                    # 没有工具调用，需要流式输出第一次调用的结果给用户
                    yield {
                        'type': 'llm_final_start',
                        'message': '无需工具调用，开始流式生成回复...',
                        'timestamp': int(time.time())
                    }
                    
                    # 如果有知识库检索结果，需要重新构建消息列表包含知识库上下文
                    final_messages = messages.copy()
                    if knowledge_results:
                        knowledge_context = self._build_knowledge_context(knowledge_results)
                        # 在原始system消息后添加知识库上下文
                        enhanced_system_content = final_messages[0]["content"] + knowledge_context
                        final_messages[0]["content"] = enhanced_system_content
                        logger.info("已添加知识库上下文到system消息")
                    
                    # 重新调用LLM进行流式输出
                    final_response = await self._call_bailian_with_function_calls(final_messages, [], stream=True)
                    
                    if final_response and 'stream_response' in final_response:
                        final_stream_response = final_response['stream_response']
                        final_full_content = ""
                        
                        try:
                            # 使用OpenAI客户端的流式处理
                            for chunk in final_stream_response:
                                if chunk.choices[0].finish_reason == "stop":
                                    break
                                else:
                                    # 实时输出消息
                                    delta = chunk.choices[0].delta
                                    if delta.content:
                                        final_full_content += delta.content
                                        # 实时返回内容片段
                                        yield {
                                            'type': 'assistant_content_chunk',
                                            'content': delta.content,
                                            'timestamp': int(time.time())
                                        }
                                        
                        except Exception as e:
                            logger.error(f"流式响应处理异常: {e}")
                            yield {
                                'type': 'error',
                                'message': f'流式响应处理异常: {str(e)}',
                                'timestamp': int(time.time())
                            }
                            return
                        
                        # 添加助手回复到数据库
                        assistant_message = self.add_message(
                            db, session_id, "assistant", final_full_content
                        )
                        
                        yield {
                            'type': 'assistant_message',
                            'message_id': assistant_message['message_id'],
                            'content': final_full_content,
                            'timestamp': int(time.time())
                        }
                        
                        # 保存对话记忆到Mem0
                        if memory_service:
                            try:
                                conversation_content = f"用户: {message_content}\n助手: {final_full_content}"
                                await memory_service.add_memory(
                                    user_id=user_id,
                                    content=conversation_content,
                                    metadata={
                                        "session_id": session_id,
                                        "assistant_id": assistant.assistant_id,
                                        "timestamp": datetime.now().isoformat(),
                                        "message_type": "conversation"
                                    },
                                    infer=True  # 使用LLM智能抽取
                                )
                                logger.info(f"对话记忆保存成功: user_id={user_id}, session_id={session_id}")
                                
                                yield {
                                    'type': 'memory_saved',
                                    'message': '对话记忆已保存',
                                    'timestamp': int(time.time())
                                }
                            except Exception as e:
                                logger.warning(f"保存对话记忆失败: {e}")
                    else:
                        yield {
                            'type': 'error',
                            'message': '流式回复生成失败',
                            'timestamp': int(time.time())
                        }
            else:
                # 第一次LLM调用失败
                yield {
                    'type': 'error',
                    'message': '大模型调用失败',
                    'timestamp': int(time.time())
                }
                    
            logger.info("流式处理完成")
            
        except Exception as e:
            logger.error(f"流式处理用户消息失败: {e}", exc_info=True)
            yield {
                'type': 'error',
                'message': f'处理失败: {str(e)}',
                'error': str(e),
                'timestamp': int(time.time())
            }

    async def _build_message_history(self, db: Session, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """构建消息历史用于Function Call上下文"""
        try:
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
            
            # 转换为标准消息格式，按时间正序排列
            history = []
            for msg in reversed(messages):
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return history
            
        except Exception as e:
            logger.error(f"构建消息历史失败: {e}")
            return []

    async def _process_message_with_function_calls(
        self, 
        message_content: str, 
        assistant: Assistant,
        message_history: List[Dict[str, Any]]
    ) -> str:
        """使用标准Function Call流程处理消息"""
        try:
            # 1. 获取可用的MCP工具并转换为Function Call格式
            available_tools = await self._get_available_function_tools(assistant)
            logger.info(f"获取到 {len(available_tools)} 个可用工具")
            
            # 2. 构建消息列表（不包含历史消息）
            messages = self._build_messages_for_llm(message_history, message_content, assistant, available_tools)
            
            # 3. 调用LLM（可能触发Function Call）
            response = await self._call_bailian_with_function_calls(messages, available_tools)
            
            # 4. 处理响应（可能包含tool_calls）
            final_content = await self._handle_function_call_response(response, assistant, messages)
            
            return final_content
            
        except Exception as e:
            logger.error(f"Function Call流程处理失败: {e}")
            return f"抱歉，处理您的消息时出现了错误：{str(e)}"
    
    async def _get_available_function_tools(self, assistant: Assistant) -> List[Dict[str, Any]]:
        """获取智能体可用的工具并转换为Function Call格式"""
        try:
            function_tools = []
            
            if hasattr(assistant, 'mcp_services') and assistant.mcp_services:
                for mcp_service in assistant.mcp_services:
                    if hasattr(mcp_service, 'mcp_server_id'):
                        server_id = mcp_service.mcp_server_id
                        
                        # 获取MCP服务的工具列表
                        try:
                            mcp_tools = await self.mcp_manager.get_server_tools(server_id)
                            
                            # 转换为Function Call格式
                            for tool in mcp_tools or []:
                                function_tool = {
                                    "type": "function",
                                    "function": {
                                        "name": f"{server_id}_{tool.get('name', 'unknown')}",
                                        "description": tool.get('description', '无描述'),
                                        "parameters": tool.get('input_schema', {
                                            "type": "object",
                                            "properties": {},
                                            "required": []
                                        })
                                    }
                                }
                                function_tools.append(function_tool)
                                
                        except Exception as e:
                            logger.warning(f"获取MCP服务 {server_id} 工具失败: {e}")
                            continue
            
            logger.info(f"获取到 {len(function_tools)} 个可用工具")
            return function_tools
                
        except Exception as e:
            logger.error(f"获取可用工具失败: {e}")
            return []

    def _build_messages_for_llm(
        self, 
        message_history: List[Dict[str, Any]], 
        current_message: str, 
        assistant: Assistant,
        available_tools: List[Dict[str, Any]],
        user_context: str = ""
    ) -> List[Dict[str, Any]]:
        """构建发送给LLM的消息列表"""
        messages = []
        
        # 1. 添加系统提示词
        system_prompt = self._build_system_prompt_for_function_calls(assistant, available_tools, user_context)
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 2. 暂不添加历史消息，只处理当前对话
        
        # 3. 添加当前用户消息
        messages.append({
            "role": "user", 
            "content": current_message
        })
        
        return messages

    def _build_system_prompt_for_function_calls(self, assistant: Assistant, available_tools: List[Dict[str, Any]] = None, user_context: str = "") -> str:
        """为Function Call构建系统提示词"""
        # 获取用户原始提示词（不包含MCP工具信息）
        base_prompt = assistant.original_prompt
        
        # 如果有用户上下文记忆，添加到提示词中
        if user_context:
            base_prompt += f"\n\n## 用户历史记忆\n\n以下是用户之前的相关对话记忆，请参考这些信息来更好地理解用户的需求和偏好：\n\n{user_context}\n\n请根据这些历史记忆来提供更个性化和相关的回复。"
        
        # 检查是否有MCP服务配置
        if hasattr(assistant, 'mcp_services') and assistant.mcp_services:
            # 构建增强提示词
            enhanced_prompt = f"""{base_prompt}

## 工具使用能力

在这个环境中，你可以使用以下MCP工具来帮助用户解决问题：

"""
            
            # 如果有可用的工具信息，添加到提示词中
            if available_tools:
                for i, tool in enumerate(available_tools):
                    tool_info = tool.get('function', {})
                    tool_name = tool_info.get('name', 'unknown')
                    tool_description = tool_info.get('description', '无描述')
                    enhanced_prompt += f"\n### 工具 {i+1}: {tool_name}\n"
                    enhanced_prompt += f"**描述**: {tool_description}\n"
                    
                    # 添加参数信息
                    parameters = tool_info.get('parameters', {})
                    if parameters and 'properties' in parameters:
                        enhanced_prompt += "**参数**:\n"
                        for param_name, param_info in parameters['properties'].items():
                            param_type = param_info.get('type', 'string')
                            param_desc = param_info.get('description', '无描述')
                            enhanced_prompt += f"- {param_name} ({param_type}): {param_desc}\n"
                    enhanced_prompt += "\n"
            else:
                enhanced_prompt += """
注意：你可以使用上述工具来帮助用户解决问题。当需要使用工具时，系统会自动调用相应的工具并返回结果。

请根据用户的需求，选择合适的工具来完成任务。如果用户的问题可以通过工具解决，请明确说明你将使用哪个工具以及如何使用。
"""
            
            return enhanced_prompt
        else:
            return base_prompt

    async def _call_bailian_with_function_calls(
        self, 
        messages: List[Dict[str, Any]], 
        available_tools: List[Dict[str, Any]],
        stream: bool = False
    ) -> Dict[str, Any]:
        """调用阿里云百炼大模型，支持Function Call和流式输出"""
        try:
            # 检查配置是否完整
            if not os.getenv("DASHSCOPE_API_KEY") or not os.getenv("DASHSCOPE_BASE_URL"):
                logger.error("阿里云百炼API配置不完整")
                return {"content": "抱歉，大模型服务配置不完整，请联系管理员。"}
            
            # 初始化 OpenAI 客户端
            client = OpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url=os.getenv("DASHSCOPE_BASE_URL")
            )
            
            # 构建请求参数
            request_params = {
                "model": "qwen-turbo",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 16384,
                "stream": stream
            }
            
            # 如果有可用工具，添加tools参数
            if available_tools:
                request_params["tools"] = available_tools
                # 检查是否是第二次调用（工具执行后的回复生成）
                is_final_response = any(msg.get('role') == 'tool' for msg in messages)
                if is_final_response:
                    # 第二次调用：强制不使用工具，专注于生成回复
                    request_params["tool_choice"] = "none"
                else:
                    # 第一次调用：让LLM自动决定是否使用工具
                    request_params["tool_choice"] = "auto"
            
            # 发送请求
            if stream:
                # 流式请求
                completion = client.chat.completions.create(**request_params)
                return {"stream_response": completion, "is_stream": True}
            else:
                # 非流式请求
                completion = client.chat.completions.create(**request_params)
                return completion.model_dump()
                        
        except Exception as e:
            logger.error(f"调用百炼大模型失败: {e}")
            return {"content": f"抱歉，调用大模型时出现错误：{str(e)}"}

    async def _handle_function_call_response(
        self, 
        response: Dict[str, Any], 
        assistant: Assistant, 
        messages: List[Dict[str, Any]]
    ) -> str:
        """处理Function Call响应"""
        try:
            logger.info("=== 开始处理Function Call响应 ===")
            logger.info(f"输入参数 - response类型: {type(response)}")
            logger.info(f"输入参数 - messages数量: {len(messages)}")
            logger.info(f"输入参数 - assistant_id: {assistant.assistant_id if hasattr(assistant, 'assistant_id') else 'unknown'}")
            
            # 检查响应格式
            logger.info("步骤1: 检查响应格式")
            if "choices" not in response or not response["choices"]:
                logger.warning("响应格式无效，缺少choices字段")
                return response.get("content", "抱歉，大模型没有返回有效响应。")
            
            choice = response["choices"][0]
            message = choice.get("message", {})
            logger.info(f"响应解析 - choice数量: {len(response['choices'])}")
            logger.debug(f"响应解析 - message详情: {message}")
            
            # 检查是否有tool_calls
            tool_calls = message.get("tool_calls")
            if tool_calls:
                logger.info(f"步骤2: 检测到工具调用，数量: {len(tool_calls)}")
                logger.debug(f"工具调用详情: {tool_calls}")
                
                # 添加assistant消息到对话历史
                logger.info("步骤3: 添加assistant消息到对话历史")
                assistant_msg = {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": tool_calls
                }
                messages.append(assistant_msg)
                logger.debug(f"添加的assistant消息: {assistant_msg}")
                
                # 执行所有工具调用
                logger.info("步骤4: 执行工具调用")
                for i, tool_call in enumerate(tool_calls):
                    logger.info(f"执行工具调用 {i+1}/{len(tool_calls)}")
                    logger.info(f"工具调用 - id: {tool_call.get('id')}")
                    logger.info(f"工具调用 - 函数名: {tool_call.get('function', {}).get('name')}")
                    logger.debug(f"工具调用详情: {tool_call}")
                    
                    tool_result = await self._execute_function_call(tool_call, assistant)
                    logger.info(f"工具执行结果 - 成功: {tool_result.get('success', False)}")
                    logger.debug(f"工具执行结果详情: {tool_result}")
                    
                    # 添加工具结果到对话历史
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    }
                    messages.append(tool_msg)
                    logger.debug(f"添加的工具结果消息: {tool_msg}")
                
                # 再次调用LLM生成最终回复
                logger.info("步骤5: 再次调用LLM生成最终回复")
                logger.info("标准Function Call流程：工具执行完成后，需要LLM生成最终回复")
                final_response = await self._call_bailian_with_function_calls(
                    messages, []  # 第二次调用不需要工具
                )
                
                logger.info("步骤6: 处理最终LLM响应")
                return await self._handle_function_call_response(final_response, assistant, messages)
            
            else:
                # 没有工具调用，直接返回内容
                logger.info("步骤2: 无工具调用，直接返回内容")
                content = message.get("content", "")
                logger.info(f"直接返回内容长度: {len(content)} 字符")
                logger.debug(f"直接返回内容: {content}")
                return content
            
        except Exception as e:
            logger.error(f"处理Function Call响应失败: {e}", exc_info=True)
            return f"抱歉，处理响应时出现错误：{str(e)}"

    async def _execute_function_call(self, tool_call: Dict[str, Any], assistant: Assistant) -> Dict[str, Any]:
        """执行单个Function Call"""
        try:
            logger.info("=== 开始执行Function Call ===")
            logger.info(f"输入参数 - tool_call类型: {type(tool_call)}")
            logger.info(f"输入参数 - assistant_id: {assistant.assistant_id if hasattr(assistant, 'assistant_id') else 'unknown'}")
            
            function_info = tool_call["function"]
            function_name = function_info["name"]
            function_args = json.loads(function_info["arguments"])
            
            logger.info(f"工具调用解析 - 函数名: {function_name}")
            logger.info(f"工具调用解析 - 参数数量: {len(function_args) if isinstance(function_args, dict) else 0}")
            logger.debug(f"工具调用解析 - 完整参数: {function_args}")
            
            # 直接使用完整的function_name作为tool_id，不需要解析
            logger.info("步骤1: 准备工具调用")
            tool_id = function_name
            logger.info(f"工具ID: {tool_id}")
            
            # 通过MCP协议执行工具
            logger.info("步骤2: 通过MCP协议执行工具")
            result = await self._execute_mcp_tool(tool_id, function_args)
            
            logger.info(f"工具执行完成 - 函数名: {function_name}")
            logger.info(f"工具执行结果 - 成功: {result.get('success', False)}")
            logger.debug(f"工具执行结果详情: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"执行工具调用失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"工具调用失败: {str(e)}"
            }

    def _validate_tool_call_schema(self, tool_call: Dict[str, Any]) -> bool:
        """Schema校验（校验1）"""
        try:
            logger.info("=== 开始Schema校验 ===")
            
            # 检查必需字段
            required_fields = ['id', 'function']
            for field in required_fields:
                if field not in tool_call:
                    logger.error(f"Schema校验失败：缺少必需字段 {field}")
                    return False
            
            function_info = tool_call.get('function', {})
            required_function_fields = ['name', 'arguments']
            for field in required_function_fields:
                if field not in function_info:
                    logger.error(f"Schema校验失败：function缺少必需字段 {field}")
                    return False
            
            # 验证arguments是否为有效JSON
            try:
                arguments = function_info.get('arguments', '{}')
                if isinstance(arguments, str):
                    json.loads(arguments)
                elif not isinstance(arguments, dict):
                    logger.error("Schema校验失败：arguments必须是JSON字符串或字典")
                    return False
            except json.JSONDecodeError as e:
                logger.error(f"Schema校验失败：arguments不是有效JSON: {e}")
                return False
            
            logger.info("Schema校验通过")
            return True
            
        except Exception as e:
            logger.error(f"Schema校验异常: {e}")
            return False

    async def _execute_mcp_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """通过MCP协议执行工具"""
        try:
            logger.info(f"开始执行MCP工具: {tool_id}")
            
            # 从环境变量获取MCP客户端URL
            mcp_client_url = os.getenv("MCP_CLIENT_URL", "http://localhost:8000")
            
            # 构建请求载荷
            request_id = f"{tool_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            payload = {
                'tool_id': tool_id,
                'arguments': arguments,
                'request_id': request_id,
                'timeout': 120
            }
            
            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{mcp_client_url}/api/v1/execution/execute',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=130)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"MCP工具调用成功: {tool_id}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"MCP工具调用失败: {tool_id}, 状态码: {response.status}")
                        return {
                            'success': False,
                            'error': f"HTTP {response.status}",
                            'message': f"MCP工具调用失败，状态码: {response.status}"
                        }
                    
        except Exception as e:
            logger.error(f"MCP工具调用失败: {tool_id}, 错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"MCP工具调用失败: {str(e)}"
            }

    async def _retrieve_knowledge_base(self, user_id: str, question: str) -> List[Dict[str, Any]]:
        """执行知识库检索"""
        try:
            logger.info(f"开始知识库检索: user_id={user_id}, question={question}")
            
            # 使用用户ID作为索引ID进行检索
            results = retrieve_content(indexNames=user_id, question=question)
            
            logger.info(f"知识库检索完成，找到 {len(results)} 个相关文档片段")
            return results
            
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return []

    def _build_knowledge_context(self, retrieval_results: List[Dict[str, Any]]) -> str:
        """构建知识库上下文"""
        if not retrieval_results:
            return ""
        
        context = "\n\n## 知识库相关信息\n"
        context += "根据知识库检索，找到以下相关内容：\n\n"
        
        for i, result in enumerate(retrieval_results, 1):
            context += f"### 文档 {i}: {result.get('document_name', '未知文档')}\n"
            context += f"**内容**: {result.get('content_with_weight', '无内容')}\n\n"
        
        context += "请基于以上知识库信息，结合你的专业知识，为用户提供准确、有用的回答。"
        return context

