"""
研究交互策略

处理研究类接口的记忆管理
"""
import logging
from typing import Dict, Any, List
from .base import InteractionStrategy

logger = logging.getLogger(__name__)


class ResearchInteractionStrategy(InteractionStrategy):
    """研究交互策略"""

    def __init__(self, memory_service=None):
        super().__init__(memory_service)
        self.strategy_name = "research"

    async def load_memories(
        self,
        user_id: str,
        input_data: Dict[str, Any],
        memory_mode: str
    ) -> List[Dict[str, Any]]:
        """
        加载研究相关记忆

        Args:
            user_id: 用户ID
            input_data: 包含question的输入数据
            memory_mode: 记忆模式

        Returns:
            研究记忆列表
        """
        question = input_data.get("question", "").strip()
        if not question:
            return []

        logger.info(f"🔍 [RESEARCH_MEMORY] 加载研究记忆，模式: {memory_mode}, 问题: {question[:50]}...")

        if memory_mode == "none":
            return []

        memories = []

        try:
            if memory_mode == "smart":
                # Smart模式：语义搜索相关研究记忆
                memories = await self._safe_search_memories(user_id, question, limit=10)
                logger.info(f"✅ [RESEARCH_MEMORY] Smart模式找到 {len(memories)} 条相关记忆")

            elif memory_mode == "short_term":
                # Short-term模式：最近的研究记忆
                all_memories = await self._safe_get_all_memories(user_id, limit=50)
                # 只获取研究类型的记忆
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") == "research"
                ][:10]
                logger.info(f"✅ [RESEARCH_MEMORY] Short-term模式找到 {len(memories)} 条最近研究记忆")

            elif memory_mode == "long_term":
                # Long-term模式：所有研究记忆
                all_memories = await self._safe_get_all_memories(user_id, limit=100)
                memories = [
                    mem for mem in all_memories
                    if mem.get("metadata", {}).get("type") == "research"
                ]
                logger.info(f"✅ [RESEARCH_MEMORY] Long-term模式找到 {len(memories)} 条历史研究记忆")

        except Exception as e:
            logger.warning(f"⚠️ [RESEARCH_MEMORY] 加载记忆失败: {e}")

        return memories

    async def save_memory(
        self,
        user_id: str,
        result_data: Dict[str, Any],
        memory_mode: str
    ) -> bool:
        """
        保存研究记忆

        Args:
            user_id: 用户ID
            result_data: 研究结果数据
            memory_mode: 记忆模式

        Returns:
            是否保存成功
        """
        if memory_mode == "none":
            return True

        # 提取研究相关信息
        question = result_data.get("question", "").strip()
        final_report = result_data.get("final_report", "")
        key_findings = result_data.get("key_findings", [])
        research_id = result_data.get("research_id", "")

        if not question:
            logger.warning("⚠️ [RESEARCH_MEMORY] 缺少研究问题，跳过保存")
            return False

        logger.info(f"💾 [RESEARCH_MEMORY] 保存研究记忆: {research_id}")

        try:
            # 构建精简的研究记忆内容
            content = self._build_research_memory_content(
                question, final_report, key_findings, result_data
            )

            # 构建元数据
            metadata = self._build_research_metadata(
                question, result_data, research_id
            )

            # 保存记忆
            success = await self._safe_add_memory(user_id, content, metadata)

            if success:
                logger.info(f"✅ [RESEARCH_MEMORY] 研究记忆保存成功: {research_id}")
                logger.info(f"📝 [RESEARCH_MEMORY] 记忆长度: {len(content)} 字符")
            else:
                logger.error(f"❌ [RESEARCH_MEMORY] 研究记忆保存失败: {research_id}")

            return success

        except Exception as e:
            logger.error(f"💥 [RESEARCH_MEMORY] 保存研究记忆异常: {e}")
            return False

    def build_context_query(self, input_data: Dict[str, Any]) -> str:
        """
        构建研究上下文查询

        Args:
            input_data: 输入数据

        Returns:
            查询字符串
        """
        question = input_data.get("question", "").strip()
        if question:
            return question

        # 备用字段
        for field in ["query", "topic", "subject"]:
            if field in input_data and input_data[field]:
                return str(input_data[field]).strip()

        return ""

    def _build_research_memory_content(
        self,
        question: str,
        final_report: str,
        key_findings: List[str],
        result_data: Dict[str, Any]
    ) -> str:
        """
        构建研究记忆内容

        采用精简策略，只存储核心信息
        """
        # 提取研究领域
        research_domain = self._extract_research_domain(question)

        # 总结关键发现（最多3个，每个限制50字符）
        findings_summary = ""
        if key_findings:
            findings_summary = "\n".join([
                f"- {finding[:50]}{'...' if len(finding) > 50 else ''}"
                for finding in key_findings[:3]
            ])

        # 构建精简内容
        content_parts = [
            f"用户研究了: {question}",
            f"研究领域: {research_domain}",
            f"研究时间: {result_data.get('timestamp', '')}"
        ]

        if findings_summary:
            content_parts.append(f"核心发现:\n{findings_summary}")

        # 添加研究质量信息
        quality_score = result_data.get("metadata", {}).get("quality_score")
        if quality_score:
            content_parts.append(f"研究质量: {quality_score}/10")

        return "\n".join(content_parts)

    def _extract_research_domain(self, question: str) -> str:
        """
        从问题中提取研究领域

        Args:
            question: 研究问题

        Returns:
            研究领域
        """
        question_lower = question.lower()

        # 技术领域关键词映射
        domain_keywords = {
            "python": "Python编程",
            "java": "Java编程",
            "javascript": "JavaScript编程",
            "机器学习": "机器学习",
            "深度学习": "深度学习",
            "人工智能": "人工智能",
            "ai": "人工智能",
            "数据科学": "数据科学",
            "大数据": "大数据",
            "前端开发": "前端开发",
            "后端开发": "后端开发",
            "全栈开发": "全栈开发",
            "区块链": "区块链",
            "云计算": "云计算",
            "微服务": "微服务架构",
            "devops": "DevOps",
            "网络安全": "网络安全",
            "算法": "算法设计"
        }

        # 查找匹配的关键词
        for keyword, domain in domain_keywords.items():
            if keyword in question_lower:
                return domain

        # 默认领域
        return "综合研究"

    def _build_research_metadata(
        self,
        question: str,
        result_data: Dict[str, Any],
        research_id: str
    ) -> Dict[str, Any]:
        """
        构建研究记忆元数据

        Args:
            question: 研究问题
            result_data: 结果数据
            research_id: 研究ID

        Returns:
            元数据字典
        """
        base_metadata = self._build_metadata(result_data, result_data, "research")

        # 添加研究特定的元数据
        research_metadata = {
            "research_id": research_id,
            "question": question,
            "domain": self._extract_research_domain(question),
            "key_findings_count": len(result_data.get("key_findings", [])),
            "word_count": len(result_data.get("final_report", "").split()),
        }

        # 添加质量相关信息
        metadata = result_data.get("metadata", {})
        if "quality_score" in metadata:
            research_metadata["quality_score"] = metadata["quality_score"]
        if "duration" in metadata:
            research_metadata["duration"] = metadata["duration"]

        # 在元数据中保留完整信息（但不参与向量搜索）
        if result_data.get("final_report"):
            research_metadata["full_report"] = result_data["final_report"][:5000]  # 保留5000字符

        if result_data.get("key_findings"):
            research_metadata["all_findings"] = result_data["key_findings"][:10]

        # 合并基础元数据
        base_metadata.update(research_metadata)

        return base_metadata