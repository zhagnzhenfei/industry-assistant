"""
研究规划代理
将用户问题转换为结构化研究简报
"""
import logging
from typing import Dict, Any, Optional

from .deep_research_types import ResearchBrief, ResearchTask

logger = logging.getLogger(__name__)


class PlanningAgent:
    """研究规划代理 - 实现write_research_brief功能"""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        """初始化规划代理"""
        self.initialized = True
        logger.info("规划代理初始化完成")

    async def cleanup(self):
        """清理资源"""
        self.initialized = False
        logger.info("规划代理资源清理完成")

    async def generate_research_brief(
        self,
        question: str,
        user_context: Optional[Dict[str, Any]] = None,
        depth: str = "comprehensive"
    ) -> ResearchBrief:
        """
        生成研究简报

        Args:
            question: 用户的研究问题
            user_context: 用户上下文
            depth: 研究深度 (basic/standard/comprehensive)

        Returns:
            ResearchBrief: 结构化研究简报
        """
        try:
            # 1. 分析问题类型
            question_type = self._analyze_question_type(question)

            # 2. 确定研究范围
            research_scope = self._determine_research_scope(question, depth)

            # 3. 提取关键研究方面
            key_aspects = self._extract_key_aspects(question, question_type, depth)

            # 4. 生成详细的研究简报
            brief_content = self._generate_brief_content(question, key_aspects)

            # 5. 估算研究时间
            estimated_duration = self._estimate_duration(key_aspects, depth)

            research_brief = ResearchBrief(
                brief=brief_content,
                scope=research_scope,
                key_aspects=key_aspects,
                estimated_duration=estimated_duration
            )

            logger.info(f"研究简报生成完成，预计耗时: {estimated_duration}分钟")
            return research_brief

        except Exception as e:
            logger.error(f"研究简报生成失败: {e}")
            # 返回默认简报
            return ResearchBrief(
                brief=f"对'{question}'进行深入研究",
                scope="基于公开数据和信息进行综合分析",
                key_aspects=["基本情况", "主要特点", "发展现状", "趋势分析"],
                estimated_duration=20
            )

    def _analyze_question_type(self, question: str) -> str:
        """分析问题类型"""
        question_lower = question.lower()

        # 公司分析
        company_keywords = ["公司", "企业", "集团", "corporation", "company", "inc"]
        if any(keyword in question_lower for keyword in company_keywords):
            return "company_analysis"

        # 行业研究
        industry_keywords = ["行业", "产业", "市场", "industry", "market", "sector"]
        if any(keyword in question_lower for keyword in industry_keywords):
            return "industry_research"

        # 产品分析
        product_keywords = ["产品", "服务", "解决方案", "product", "service", "solution"]
        if any(keyword in question_lower for keyword in product_keywords):
            return "product_analysis"

        # 技术分析
        tech_keywords = ["技术", "科技", "创新", "technology", "innovation", "tech"]
        if any(keyword in question_lower for keyword in tech_keywords):
            return "technology_analysis"

        # 趋势分析
        trend_keywords = ["趋势", "发展", "前景", "未来", "trend", "future", "outlook"]
        if any(keyword in question_lower for keyword in trend_keywords):
            return "trend_analysis"

        # 比较分析
        comparison_keywords = ["比较", "对比", "vs", "versus", "compare", "comparison"]
        if any(keyword in question_lower for keyword in comparison_keywords):
            return "comparison_analysis"

        # 默认为综合分析
        return "comprehensive_analysis"

    def _determine_research_scope(self, question: str, depth: str) -> str:
        """确定研究范围"""
        question_lower = question.lower()

        # 地理范围检测
        if "中国" in question_lower or "国内" in question_lower:
            geographic_scope = "主要关注中国市场"
        elif "全球" in question_lower or "国际" in question_lower or "world" in question_lower:
            geographic_scope = "全球范围分析"
        elif "美国" in question_lower or "欧洲" in question_lower or "亚洲" in question_lower:
            geographic_scope = f"重点关注{question_lower.split('美国')[0].split('欧洲')[0].split('亚洲')[0]}市场"
        else:
            geographic_scope = "基于全球公开数据和信息"

        # 深度范围
        if depth == "basic":
            detail_level = "基础层面的分析"
        elif depth == "standard":
            detail_level = "标准深度的综合分析"
        else:  # comprehensive
            detail_level = "深度全面的综合分析"

        return f"{geographic_scope}，{detail_level}"

    def _extract_key_aspects(self, question: str, question_type: str, depth: str) -> list:
        """提取关键研究方面"""
        base_aspects = ["基本情况", "主要特点", "发展现状", "趋势分析"]

        # 根据问题类型添加特定方面
        if question_type == "company_analysis":
            company_aspects = ["财务状况", "业务模式", "竞争优势", "管理团队", "风险因素"]
            if depth == "comprehensive":
                base_aspects.extend(company_aspects)
            elif depth == "standard":
                base_aspects.extend(["财务状况", "业务模式", "竞争优势"])

        elif question_type == "industry_research":
            industry_aspects = ["市场规模", "竞争格局", "政策环境", "技术发展", "投资机会"]
            if depth == "comprehensive":
                base_aspects.extend(industry_aspects)
            elif depth == "standard":
                base_aspects.extend(["市场规模", "竞争格局", "政策环境"])

        elif question_type == "product_analysis":
            product_aspects = ["产品功能", "用户体验", "市场表现", "竞争对手", "技术优势"]
            if depth == "comprehensive":
                base_aspects.extend(product_aspects)
            elif depth == "standard":
                base_aspects.extend(["产品功能", "用户体验", "市场表现"])

        elif question_type == "technology_analysis":
            tech_aspects = ["技术原理", "应用场景", "发展历程", "技术优势", "未来趋势"]
            if depth == "comprehensive":
                base_aspects.extend(tech_aspects)
            elif depth == "standard":
                base_aspects.extend(["技术原理", "应用场景", "未来趋势"])

        elif question_type == "comparison_analysis":
            comparison_aspects = ["对比维度", "各自优势", "适用场景", "成本效益", "发展前景"]
            if depth == "comprehensive":
                base_aspects.extend(comparison_aspects)
            elif depth == "standard":
                base_aspects.extend(["对比维度", "各自优势", "适用场景"])

        # 去重并限制数量
        unique_aspects = list(dict.fromkeys(base_aspects))  # 去重保持顺序
        return unique_aspects[:8]  # 最多8个方面

    def _generate_brief_content(self, question: str, key_aspects: list) -> str:
        """生成详细的研究简报内容"""
        brief_parts = [
            f"对'{question}'进行深入研究",
            f"重点分析以下{len(key_aspects)}个核心方面："
        ]

        # 添加具体的研究方面
        for i, aspect in enumerate(key_aspects, 1):
            brief_parts.append(f"{i}. {aspect}")

        # 添加研究方法说明
        brief_parts.append("\n研究方法：采用多源数据收集、交叉验证、趋势分析等方法")
        brief_parts.append("数据来源：基于公开的财务报告、行业分析、新闻报道等可靠信息")

        return "\n".join(brief_parts)

    def _estimate_duration(self, key_aspects: list, depth: str) -> int:
        """估算研究时间（分钟）"""
        base_time = len(key_aspects) * 3  # 每个方面基础3分钟

        # 根据深度调整
        if depth == "basic":
            multiplier = 0.8
        elif depth == "standard":
            multiplier = 1.2
        else:  # comprehensive
            multiplier = 1.5

        estimated_time = int(base_time * multiplier)

        # 设置合理的范围
        return max(10, min(60, estimated_time))  # 10-60分钟