"""
用户澄清代理
分析用户问题，判断是否需要澄清
"""
import logging
from typing import Dict, Any, Optional

from .deep_research_types import ClarificationRequest

logger = logging.getLogger(__name__)


class ClarificationAgent:
    """用户澄清代理 - 实现clarify_with_user功能"""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        """初始化澄清代理"""
        self.initialized = True
        logger.info("澄清代理初始化完成")

    async def cleanup(self):
        """清理资源"""
        self.initialized = False
        logger.info("澄清代理资源清理完成")

    async def analyze_clarification_need(
        self,
        question: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> ClarificationRequest:
        """
        分析是否需要澄清问题

        Args:
            question: 用户的研究问题
            user_context: 用户上下文信息

        Returns:
            ClarificationRequest: 澄清请求结果
        """
        try:
            question_lower = question.lower().strip()

            # 规则1: 检查问题长度
            if len(question) < 10:
                return ClarificationRequest(
                    need_clarification=True,
                    question="您的问题比较简短，能否提供更多详细信息？比如您希望了解的具体方面、时间范围、地理区域等。",
                    reason="问题过于简短，需要更多背景信息"
                )

            # 规则2: 检查是否包含具体的研究对象
            specific_entities = [
                "公司", "行业", "市场", "产品", "技术", "股票", "品牌",
                "country", "country的", "中国", "美国", "欧洲", "亚洲"
            ]

            has_specific_entity = any(entity in question_lower for entity in specific_entities)

            if not has_specific_entity:
                return ClarificationRequest(
                    need_clarification=True,
                    question="您想研究具体的哪个公司、行业、产品或主题？请提供一个更具体的研究对象。",
                    reason="缺乏具体的研究对象"
                )

            # 规则3: 检查是否包含时间范围
            time_indicators = ["2023", "2024", "2025", "今年", "去年", "近期", "未来", "过去"]
            has_time_context = any(indicator in question_lower for indicator in time_indicators)

            if not has_time_context:
                # 不强制要求时间范围，给出建议但不停止流程
                return ClarificationRequest(
                    need_clarification=False,
                    question="",
                    verification=f"已理解您关于{question}的研究需求。由于没有指定时间范围，我将主要关注近期的发展情况。如果您有特定的时间要求，可以在后续研究中补充。",
                    reason="时间范围可选，继续研究流程"
                )

            # 规则4: 检查是否有模糊的表述
            vague_terms = ["怎么样", "如何", "什么", "为什么", "怎么样了"]
            if question in vague_terms or len(question.split()) < 3:
                return ClarificationRequest(
                    need_clarification=True,
                    question="您的问题表述比较模糊，能否更具体地描述您想了解的内容？",
                    reason="问题表述模糊，需要更具体的描述"
                )

            # 规则5: 检查是否有明确的研究意图
            research_indicators = [
                "分析", "研究", "比较", "评估", "调查", "了解", "探讨",
                "发展", "趋势", "现状", "前景", "情况", "问题", "挑战", "机遇"
            ]

            has_research_intent = any(indicator in question_lower for indicator in research_indicators)

            if not has_research_intent:
                return ClarificationRequest(
                    need_clarification=False,
                    question="",
                    verification=f"已理解您对{question}的研究需求。我将从多个角度为您分析这个主题。",
                    reason="虽然没有明确的研究动词，但上下文表明有研究意图"
                )

            # 通过所有检查，无需澄清
            return ClarificationRequest(
                need_clarification=False,
                question="",
                verification=f"已充分理解您的研究需求：{question}。现在开始为您进行深度研究分析。",
                reason="问题清晰，研究意图明确"
            )

        except Exception as e:
            logger.error(f"澄清分析失败: {e}")
            # 出错时保守处理，继续流程
            return ClarificationRequest(
                need_clarification=False,
                question="",
                verification=f"已接收您的研究请求：{question}。现在开始进行分析。",
                reason="分析过程出现错误，继续执行研究流程"
            )