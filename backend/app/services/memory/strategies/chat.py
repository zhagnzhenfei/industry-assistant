"""
聊天交互策略

处理聊天类接口的记忆管理
"""
import logging
from typing import Dict, Any, List
from .base import InteractionStrategy

logger = logging.getLogger(__name__)


class ChatInteractionStrategy(InteractionStrategy):
    """聊天交互策略"""

    def __init__(self, memory_service=None):
        super().__init__(memory_service)
        self.strategy_name = "chat"

    async def load_memories(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        memory_mode: str
    ) -> List[Dict[str, Any]]:
        """
        加载聊天相关记忆

        Args:
            user_id: 用户ID
            input_data: 包含message的输入数据
            memory_mode: 记忆模式

        Returns:
            聊天记忆列表
        """
        message = input_data.get("message", "").strip()
        if not message:
            return []

        logger.info(f"🔍 [CHAT_MEMORY] 加载聊天记忆，模式: {memory_mode}, 消息: {message[:50]}...")

        if memory_mode == "none":
            return []

        memories = []

        try:
            if memory_mode == "smart":
                # Smart模式：语义搜索相关聊天历史
                memories = await self._safe_search_memories(user_id, message, limit=5)
                logger.info(f"✅ [CHAT_MEMORY] Smart模式找到 {len(memories)} 条相关聊天记忆")

            elif memory_mode == "short_term":
                # Short-term模式：最近的聊天记录
                all_memories = await self._safe_get_all_memories(user_id, limit=30)
                # 只获取聊天类型的记忆
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") == "chat"
                ][:10]
                logger.info(f"✅ [CHAT_MEMORY] Short-term模式找到 {len(memories)} 条最近聊天记忆")

            elif memory_mode == "long_term":
                # Long-term模式：所有聊天记忆
                all_memories = await self._safe_get_all_memories(user_id, limit=100)
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") == "chat"
                ]
                logger.info(f"✅ [CHAT_MEMORY] Long-term模式找到 {len(memories)} 条历史聊天记忆")

        except Exception as e:
            logger.warning(f"⚠️ [CHAT_MEMORY] 加载记忆失败: {e}")

        return memories

    async def save_memory(
        self,
        user_id: str,
        result_data: Dict[str, Any],
        memory_mode: str
    ) -> bool:
        """
        保存聊天记忆

        Args:
            user_id: 用户ID
            result_data: 聊天结果数据
            memory_mode: 记忆模式

        Returns:
            是否保存成功
        """
        if memory_mode == "none":
            return True

        # 提取聊天相关信息
        user_message = result_data.get("user_message", "").strip()
        ai_response = result_data.get("ai_response", "").strip()
        session_id = result_data.get("session_id", "")

        if not user_message or not ai_response:
            logger.warning("⚠️ [CHAT_MEMORY] 缺少用户消息或AI响应，跳过保存")
            return False

        logger.info(f"💾 [CHAT_MEMORY] 保存聊天记忆，会话: {session_id}")

        try:
            # 构建聊天记忆内容
            content = self._build_chat_memory_content(user_message, ai_response, result_data)

            # 构建元数据
            metadata = self._build_chat_metadata(user_message, ai_response, result_data, session_id)

            # 保存记忆
            success = await self._safe_add_memory(user_id, content, metadata)

            if success:
                logger.info(f"✅ [CHAT_MEMORY] 聊天记忆保存成功")
                logger.info(f"📝 [CHAT_MEMORY] 记忆长度: {len(content)} 字符")
            else:
                logger.error(f"❌ [CHAT_MEMORY] 聊天记忆保存失败")

            return success

        except Exception as e:
            logger.error(f"💥 [CHAT_MEMORY] 保存聊天记忆异常: {e}")
            return False

    def build_context_query(self, input_data: Dict[str, Any]) -> str:
        """
        构建聊天上下文查询

        Args:
            input_data: 输入数据

        Returns:
            查询字符串
        """
        message = input_data.get("message", "").strip()
        if message:
            return message

        # 备用字段
        for field in ["query", "prompt", "input", "question"]:
            if field in input_data and input_data[field]:
                return str(input_data[field]).strip()

        return ""

    def _build_chat_memory_content(
        self,
        user_message: str,
        ai_response: str,
        result_data: Dict[str, Any]
    ) -> str:
        """
        构建聊天记忆内容

        保存完整的对话内容，便于上下文理解
        """
        content_parts = [
            f"用户: {user_message}",
            f"助手: {ai_response}"
        ]

        # 添加对话摘要（可选）
        summary = result_data.get("summary", "")
        if summary:
            content_parts.append(f"摘要: {summary}")

        # 添加对话类型标签
        conversation_type = self._classify_conversation(user_message)
        if conversation_type:
            content_parts.append(f"对话类型: {conversation_type}")

        return "\n".join(content_parts)

    def _classify_conversation(self, user_message: str) -> str:
        """
        分类对话类型

        Args:
            user_message: 用户消息

        Returns:
            对话类型
        """
        message_lower = user_message.lower()

        # 问题类型
        if any(keyword in message_lower for keyword in ["什么", "为什么", "如何", "怎么", "?", "？"]):
            return "问答"

        # 请求类型
        if any(keyword in message_lower for keyword in ["请", "帮我", "能否", "可以", "需要"]):
            return "请求"

        # 信息分享
        if any(keyword in message_lower for keyword in ["我觉得", "我认为", "我想", "我的"]):
            return "分享"

        # 情感表达
        if any(keyword in message_lower for keyword in ["谢谢", "感谢", "好的", "不错", "太好了"]):
            return "情感"

        # 问候
        if any(keyword in message_lower for keyword in ["你好", "hello", "hi", "早上好", "晚上好"]):
            return "问候"

        return "一般对话"

    def _build_chat_metadata(
        self,
        user_message: str,
        ai_response: str,
        result_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        构建聊天记忆元数据

        Args:
            user_message: 用户消息
            ai_response: AI响应
            result_data: 结果数据
            session_id: 会话ID

        Returns:
            元数据字典
        """
        base_metadata = self._build_metadata(result_data, result_data, "chat")

        # 添加聊天特定的元数据
        chat_metadata = {
            "session_id": session_id,
            "conversation_type": self._classify_conversation(user_message),
            "user_message_length": len(user_message),
            "ai_response_length": len(ai_response),
            "exchange_id": result_data.get("exchange_id", ""),
        }

        # 分析用户意图（简单版）
        intent = self._extract_user_intent(user_message)
        if intent:
            chat_metadata["user_intent"] = intent

        # 添加情感分析（简单版）
        sentiment = self._analyze_sentiment(user_message)
        chat_metadata["sentiment"] = sentiment

        # 合并基础元数据
        base_metadata.update(chat_metadata)

        return base_metadata

    def _extract_user_intent(self, user_message: str) -> str:
        """
        提取用户意图

        Args:
            user_message: 用户消息

        Returns:
            用户意图
        """
        message_lower = user_message.lower()

        # 意图关键词映射
        intent_keywords = {
            "search": ["搜索", "查找", "找", "search", "find"],
            "learn": ["学习", "了解", "教", "learn", "understand"],
            "create": ["创建", "生成", "写", "create", "generate", "write"],
            "help": ["帮助", "协助", "help", "assist"],
            "analyze": ["分析", "分析一下", "analyze", "analysis"],
            "recommend": ["推荐", "建议", "recommend", "suggest"],
            "compare": ["比较", "对比", "compare", "difference"],
            "explain": ["解释", "说明", "explain", "explanation"]
        }

        # 查找匹配的意图
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent

        return "general"

    def _analyze_sentiment(self, user_message: str) -> str:
        """
        简单的情感分析

        Args:
            user_message: 用户消息

        Returns:
            情感标签
        """
        message_lower = user_message.lower()

        # 正面情感关键词
        positive_words = ["好", "棒", "赞", "不错", "太好了", "满意", "谢谢", "感谢", "good", "great", "awesome", "thanks"]

        # 负面情感关键词
        negative_words = ["不好", "糟糕", "差", "失望", "生气", "不满", "bad", "terrible", "disappointed", "angry"]

        # 计算情感分数
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"