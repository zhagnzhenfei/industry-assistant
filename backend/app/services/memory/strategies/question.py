"""
问答交互策略

处理简单问答类接口的记忆管理
"""
import logging
from typing import Dict, Any, List
from .base import InteractionStrategy

logger = logging.getLogger(__name__)


class QuestionInteractionStrategy(InteractionStrategy):
    """问答交互策略"""

    def __init__(self, memory_service=None):
        super().__init__(memory_service)
        self.strategy_name = "question"

    async def load_memories(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        memory_mode: str
    ) -> List[Dict[str, Any]]:
        """
        加载问答相关记忆

        Args:
            user_id: 用户ID
            input_data: 包含question的输入数据
            memory_mode: 记忆模式

        Returns:
            问答记忆列表
        """
        question = input_data.get("question", "").strip()
        if not question:
            return []

        logger.info(f"🔍 [QUESTION_MEMORY] 加载问答记忆，模式: {memory_mode}, 问题: {question[:50]}...")

        if memory_mode == "none":
            return []

        memories = []

        try:
            if memory_mode == "smart":
                # Smart模式：语义搜索相关的问答记忆
                memories = await self._safe_search_memories(user_id, question, limit=5)
                logger.info(f"✅ [QUESTION_MEMORY] Smart模式找到 {len(memories)} 条相关问答记忆")

            elif memory_mode == "short_term":
                # Short-term模式：最近的问答记录
                all_memories = await self._safe_get_all_memories(user_id, limit=20)
                # 获取问答和事实类型的记忆
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") in ["question", "fact"]
                ][:8]
                logger.info(f"✅ [QUESTION_MEMORY] Short-term模式找到 {len(memories)} 条最近问答记忆")

            elif memory_mode == "long_term":
                # Long-term模式：所有问答记忆
                all_memories = await self._safe_get_all_memories(user_id, limit=50)
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") in ["question", "fact"]
                ]
                logger.info(f"✅ [QUESTION_MEMORY] Long-term模式找到 {len(memories)} 条历史问答记忆")

        except Exception as e:
            logger.warning(f"⚠️ [QUESTION_MEMORY] 加载记忆失败: {e}")

        return memories

    async def save_memory(
        self,
        user_id: str,
        result_data: Dict[str, Any],
        memory_mode: str
    ) -> bool:
        """
        保存问答记忆

        Args:
            user_id: 用户ID
            result_data: 问答结果数据
            memory_mode: 记忆模式

        Returns:
            是否保存成功
        """
        if memory_mode == "none":
            return True

        # 提取问答相关信息
        question = result_data.get("question", "").strip()
        answer = result_data.get("answer", "").strip()

        if not question or not answer:
            logger.warning("⚠️ [QUESTION_MEMORY] 缺少问题或答案，跳过保存")
            return False

        # 检查是否值得保存
        if not self.should_save_memory({"question": question}, {"answer": answer}):
            logger.info(f"ℹ️ [QUESTION_MEMORY] 问题不值得保存，跳过: {question[:30]}...")
            return True

        logger.info(f"💾 [QUESTION_MEMORY] 保存问答记忆")

        try:
            # 构建问答记忆内容
            content = self._build_question_memory_content(question, answer, result_data)

            # 构建元数据
            metadata = self._build_question_metadata(question, answer, result_data)

            # 保存记忆
            success = await self._safe_add_memory(user_id, content, metadata)

            if success:
                logger.info(f"✅ [QUESTION_MEMORY] 问答记忆保存成功")
                logger.info(f"📝 [QUESTION_MEMORY] 记忆长度: {len(content)} 字符")
            else:
                logger.error(f"❌ [QUESTION_MEMORY] 问答记忆保存失败")

            return success

        except Exception as e:
            logger.error(f"💥 [QUESTION_MEMORY] 保存问答记忆异常: {e}")
            return False

    def build_context_query(self, input_data: Dict[str, Any]) -> str:
        """
        构建问答上下文查询

        Args:
            input_data: 输入数据

        Returns:
            查询字符串
        """
        question = input_data.get("question", "").strip()
        if question:
            return question

        # 备用字段
        for field in ["query", "prompt", "message", "input"]:
            if field in input_data and input_data[field]:
                return str(input_data[field]).strip()

        return ""

    def should_save_memory(self, input_data: Dict[str, Any], result_data: Dict[str, Any]) -> bool:
        """
        判断问答是否值得保存

        Args:
            input_data: 包含问题的输入数据
            result_data: 包含答案的结果数据

        Returns:
            是否应该保存
        """
        # 使用基类的过滤逻辑
        if not super().should_save_memory(input_data, result_data):
            return False

        question = self._extract_user_input(input_data)
        answer = self._extract_user_response(result_data)

        # 问答特定的过滤规则

        # 1. 过滤太简单的问答
        simple_patterns = [
            r"^你好",
            r"^谢谢",
            r"^再见",
            r"^ok$",
            r"^好的$",
            r"^是的$",
            r"^不是$",
            r"^hello",
            r"^hi$",
            r"^bye"
        ]

        import re
        for pattern in simple_patterns:
            if re.match(pattern, question.lower()):
                return False

        # 2. 确保答案有实际内容
        if len(answer) < 10:
            return False

        # 3. 过滤纯客套话
        courtesy_phrases = ["不客气", "不用谢", "没关系", "you're welcome", "no problem"]
        if answer.lower() in courtesy_phrases:
            return False

        return True

    def _build_question_memory_content(
        self,
        question: str,
        answer: str,
        result_data: Dict[str, Any]
    ) -> str:
        """
        构建问答记忆内容

        保存问答对，便于后续检索和参考
        """
        content_parts = [
            f"问: {question}",
            f"答: {answer}"
        ]

        # 添加分类标签
        category = self._classify_question(question)
        if category:
            content_parts.append(f"分类: {category}")

        return "\n".join(content_parts)

    def _classify_question(self, question: str) -> str:
        """
        分类问题类型

        Args:
            question: 问题

        Returns:
            问题分类
        """
        question_lower = question.lower()

        # 技术问题
        if any(keyword in question_lower for keyword in ["如何", "怎么", "怎样", "how to", "how"]):
            return "方法指导"

        # 概念解释
        if any(keyword in question_lower for keyword in ["什么", "是什么", "定义", "what is", "define"]):
            return "概念解释"

        # 原理说明
        if any(keyword in question_lower for keyword in ["为什么", "why", "原理"]):
            return "原理说明"

        # 比较对比
        if any(keyword in question_lower for keyword in ["比较", "对比", "区别", "difference", "compare"]):
            return "对比分析"

        # 推荐建议
        if any(keyword in question_lower for keyword in ["推荐", "建议", "哪个好", "recommend", "suggest"]):
            return "推荐建议"

        # 故障排查
        if any(keyword in question_lower for keyword in ["错误", "问题", "故障", "bug", "error", "issue"]):
            return "故障排查"

        # 最佳实践
        if any(keyword in question_lower for keyword in ["最佳", "最好", "优化", "best", "optimal", "optimize"]):
            return "最佳实践"

        return "一般问答"

    def _build_question_metadata(
        self,
        question: str,
        answer: str,
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建问答记忆元数据

        Args:
            question: 问题
            answer: 答案
            result_data: 结果数据

        Returns:
            元数据字典
        """
        base_metadata = self._build_metadata(result_data, result_data, "question")

        # 添加问答特定的元数据
        question_metadata = {
            "question": question,
            "answer_length": len(answer),
            "question_length": len(question),
            "category": self._classify_question(question),
            "question_id": result_data.get("question_id", ""),
        }

        # 提取关键词
        keywords = self._extract_keywords(question)
        if keywords:
            question_metadata["keywords"] = keywords

        # 分析问题复杂度
        complexity = self._analyze_question_complexity(question, answer)
        question_metadata["complexity"] = complexity

        # 检测是否为事实性问题
        is_factual = self._is_factual_question(question)
        if is_factual:
            question_metadata["type"] = "fact"

        # 合并基础元数据
        base_metadata.update(question_metadata)

        return base_metadata

    def _extract_keywords(self, question: str) -> List[str]:
        """
        提取问题关键词

        Args:
            question: 问题

        Returns:
            关键词列表
        """
        import re

        # 简单的关键词提取
        # 移除标点符号
        clean_question = re.sub(r'[^\w\s]', '', question)

        # 分词
        words = clean_question.split()

        # 过滤停用词和短词
        stop_words = {
            "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "这", "个",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"
        }

        keywords = [
            word for word in words
            if len(word) > 1 and word.lower() not in stop_words
        ]

        # 返回前5个关键词
        return keywords[:5]

    def _analyze_question_complexity(self, question: str, answer: str) -> str:
        """
        分析问题复杂度

        Args:
            question: 问题
            answer: 答案

        Returns:
            复杂度标签
        """
        # 基于问题长度和关键词的简单分析
        question_length = len(question)
        answer_length = len(answer)

        # 复杂度指标
        complexity_score = 0

        # 问题长度贡献
        if question_length > 50:
            complexity_score += 1
        if question_length > 100:
            complexity_score += 1

        # 答案长度贡献
        if answer_length > 200:
            complexity_score += 1
        if answer_length > 500:
            complexity_score += 1

        # 关键词贡献
        complex_keywords = ["如何实现", "原理是什么", "详细说明", "深入分析", "step by step"]
        for keyword in complex_keywords:
            if keyword in question.lower():
                complexity_score += 1

        # 分类复杂度
        if complexity_score <= 1:
            return "简单"
        elif complexity_score <= 3:
            return "中等"
        else:
            return "复杂"

    def _is_factual_question(self, question: str) -> bool:
        """
        判断是否为事实性问题

        Args:
            question: 问题

        Returns:
            是否为事实性问题
        """
        question_lower = question.lower()

        factual_patterns = [
            r"什么是",
            r"定义",
            r"定义是",
            r"多少",
            r"几个",
            r"何时",
            r"哪里",
            r"谁",
            r"what is",
            r"define",
            r"how many",
            r"how much",
            r"when",
            r"where",
            r"who"
        ]

        import re
        for pattern in factual_patterns:
            if re.search(pattern, question_lower):
                return True

        return False