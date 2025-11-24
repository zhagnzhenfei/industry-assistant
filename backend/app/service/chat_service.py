#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一聊天服务 - 使用Milvus作为向量数据库
整合V1和V2版本功能，基于Milvus进行文档检索
"""

import json
import os
from typing import List, Dict, Any, Optional, Generator
import uuid
from openai import OpenAI
import numpy as np
import tiktoken

from .document_management_service import DocumentManagementService
from .web_search_service import WebSearchService
from .session_service import SessionService
from utils.database import default_manager
from models import Document
from service.core.rag.nlp.model import generate_embedding
from pymilvus import connections, Collection, utility

logger = __import__('logging').getLogger(__name__)


class UnifiedChatService:
    """
    统一聊天服务

    功能特性：
    1. 基于Milvus的向量检索
    2. Web搜索集成
    3. 会话管理
    4. 文档重排序
    5. 流式响应生成
    """

    def __init__(self, document_service: DocumentManagementService, web_search_service: WebSearchService, session_service: SessionService):
        """
        初始化统一聊天服务

        Args:
            document_service: 文档管理服务
            web_search_service: Web搜索服务
            session_service: 会话管理服务
        """
        self.document_service = document_service
        self.web_search_service = web_search_service
        self.session_service = session_service

        # OpenAI/DashScope配置 - 安全要求：必须设置API密钥
        self.openai_api_key = os.environ.get("DASHSCOPE_API_KEY")
        self.openai_base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.openai_model = os.environ.get("OPENAI_MODEL", "qwen-turbo")

        # 安全验证：API密钥不能为空
        if not self.openai_api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable is required and cannot be empty")

        # Token计算
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = 12000

        # Milvus配置
        self.milvus_host = os.environ.get("MILVUS_HOST", "localhost")
        self.milvus_port = int(os.environ.get("MILVUS_PORT", "19530"))
        self.collection_name = "document_chunks"

        # 初始化Milvus连接
        self._init_milvus()

    def _init_milvus(self):
        """初始化Milvus连接"""
        try:
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port
            )

            # 检查collection是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.collection.load()
                logger.info(f"✅ 已连接到Milvus集合: {self.collection_name}")
            else:
                logger.warning(f"⚠️ Milvus集合不存在: {self.collection_name}")
                self.collection = None

        except Exception as e:
            logger.error(f"❌ 连接Milvus失败: {e}")
            self.collection = None

    def retrieve_from_milvus(self, question: str, user_id: str = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        从Milvus检索相关文档

        Args:
            question: 用户问题
            user_id: 用户ID（可选，用于过滤用户文档）
            top_k: 返回结果数量

        Returns:
            检索到的文档列表
        """
        if not self.collection:
            logger.error("Milvus连接不可用")
            return []

        try:
            # 生成问题向量
            question_embedding = generate_embedding(question)

            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 16}
            }

            # 构建表达式（可选的用户过滤）
            expr = f"user_id == '{user_id}'" if user_id else None

            # 执行向量搜索
            results = self.collection.search(
                data=[question_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["content", "document_id", "chunk_id", "file_name", "user_id"]
            )

            # 格式化结果
            documents = []
            for hits in results:
                for hit in hits:
                    documents.append({
                        "content": hit.entity.get("content", ""),
                        "document_id": hit.entity.get("document_id", ""),
                        "chunk_id": hit.entity.get("chunk_id", ""),
                        "file_name": hit.entity.get("file_name", ""),
                        "user_id": hit.entity.get("user_id", ""),
                        "score": float(hit.score),
                        "source": "milvus"
                    })

            logger.info(f"🔍 从Milvus检索到 {len(documents)} 个相关文档")
            return documents

        except Exception as e:
            logger.error(f"❌ Milvus检索失败: {e}")
            return []

    def retrieve_from_web(self, question: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        从Web搜索获取信息

        Args:
            question: 搜索问题
            num_results: 搜索结果数量

        Returns:
            Web搜索结果列表
        """
        try:
            results = self.web_search_service.search(question, num_results=num_results)

            web_docs = []
            for result in results:
                web_docs.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0),
                    "source": "web"
                })

            logger.info(f"🌐 从Web搜索到 {len(web_docs)} 个结果")
            return web_docs

        except Exception as e:
            logger.error(f"❌ Web搜索失败: {e}")
            return []

    def rerank_documents(self, question: str, documents: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        重排序文档

        Args:
            question: 用户问题
            documents: 文档列表
            top_n: 返回文档数量

        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []

        try:
            # 按分数排序
            documents.sort(key=lambda x: x.get("score", 0), reverse=True)

            # 返回前N个文档
            return documents[:top_n]

        except Exception as e:
            logger.error(f"❌ 文档重排序失败: {e}")
            return documents[:top_n]

    def _build_context(self, documents: List[Dict[str, Any]], max_tokens: int = 8000) -> str:
        """
        构建上下文文本

        Args:
            documents: 文档列表
            max_tokens: 最大token数

        Returns:
            上下文文本
        """
        context_parts = []
        current_tokens = 0

        for doc in documents:
            content = doc.get("content", "") or doc.get("snippet", "")
            if not content:
                continue

            # 计算token数量
            tokens = len(self.encoding.encode(content))

            if current_tokens + tokens > max_tokens:
                # 截断文档内容
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # 至少保留100个token
                    truncated = self.encoding.decode(self.encoding.encode(content)[:remaining_tokens])
                    context_parts.append(f"[{doc.get('source', 'unknown')}] {truncated}")
                break

            context_parts.append(f"[{doc.get('source', 'unknown')}] {content}")
            current_tokens += tokens

        return "\n\n".join(context_parts)

    def get_chat_completion(
        self,
        session_id: str,
        question: str,
        retrieved_content: List[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        生成聊天回复（流式）

        Args:
            session_id: 会话ID
            question: 用户问题
            retrieved_content: 检索到的文档内容

        Yields:
            流式回复内容
        """
        try:
            # 获取会话历史
            session_history = self.session_service.get_history(session_id)

            # 构建上下文
            context = ""
            if retrieved_content:
                context = self._build_context(retrieved_content)

            # 构建系统提示
            system_prompt = f"""你是一个智能问答助手。请基于以下检索到的文档内容回答用户问题。

检索到的相关文档：
{context}

请根据上述文档内容回答用户的问题。如果文档中没有相关信息，请诚实地说明，并尽可能提供有用的建议。

用户问题：{question}

回答："""

            # 调用OpenAI API生成回复
            client = OpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url
            )

            # 构建消息历史
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # 添加会话历史
            for msg in session_history[-10:]:  # 最近10条消息
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # 添加当前问题
            messages.append({"role": "user", "content": question})

            # 发送流式请求
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )

            # 收集完整回复用于保存会话
            full_reply = ""

            # 流式输出
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_reply += content

                    # SSE格式输出
                    yield f"data: {json.dumps({'content': content, 'type': 'message'}, ensure_ascii=False)}\n\n"

            # 保存会话
            self.session_service.add_message(session_id, "user", question)
            self.session_service.add_message(session_id, "assistant", full_reply)

            # 结束标记
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"❌ 生成聊天回复失败: {e}")
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'}, ensure_ascii=False)}\n\n"