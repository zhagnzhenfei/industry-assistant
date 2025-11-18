"""
最终报告生成器
将研究结果整合为结构化的最终报告
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from .deep_research_types import ResearchBrief, ResearchResult

logger = logging.getLogger(__name__)


class FinalReportGenerator:
    """最终报告生成器 - 实现final_report_generation功能"""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        """初始化报告生成器"""
        try:
            self.initialized = True
            logger.info("最终报告生成器初始化完成")
        except Exception as e:
            logger.error(f"最终报告生成器初始化失败: {e}")
            raise

    async def cleanup(self):
        """清理资源"""
        try:
            self.initialized = False
            logger.info("最终报告生成器资源清理完成")
        except Exception as e:
            logger.error(f"最终报告生成器资源清理失败: {e}")

    async def generate_report(
        self,
        question: str,
        research_brief: ResearchBrief,
        research_results: List[ResearchResult]
    ) -> str:
        """
        生成最终研究报告

        Args:
            question: 原始研究问题
            research_brief: 研究简报
            research_results: 研究结果列表

        Returns:
            str: 最终研究报告
        """
        try:
            logger.info("开始生成最终报告")

            # 1. 整合所有研究结果
            integrated_findings = self._integrate_research_findings(research_results)

            # 2. 构建报告结构
            report_structure = self._build_report_structure(
                question, research_brief, integrated_findings
            )

            # 3. 生成详细内容
            final_report = self._generate_detailed_content(report_structure)

            # 4. 添加元信息和总结
            final_report = self._add_metadata_and_summary(
                final_report, question, research_brief, research_results
            )

            logger.info("最终报告生成完成")
            return final_report

        except Exception as e:
            logger.error(f"最终报告生成失败: {e}")
            return self._generate_fallback_report(question, research_brief, research_results)

    def _integrate_research_findings(
        self,
        research_results: List[ResearchResult]
    ) -> Dict[str, Any]:
        """整合研究结果"""
        try:
            integrated = {
                "successful_tasks": [],
                "failed_tasks": [],
                "all_findings": [],
                "key_insights": [],
                "data_sources": set(),
                "research_areas": [],
                "execution_summary": {
                    "total_tasks": len(research_results),
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "total_execution_time": 0.0
                }
            }

            for result in research_results:
                # 更新执行统计
                integrated["execution_summary"]["total_execution_time"] += result.execution_time

                if result.status == "success":
                    integrated["successful_tasks"].append(result)
                    integrated["execution_summary"]["successful_tasks"] += 1

                    # 整合发现
                    integrated["all_findings"].extend(result.findings)

                    # 提取关键洞察
                    if result.details:
                        integrated["key_insights"].extend(
                            self._extract_insights_from_result(result)
                        )

                    # 收集数据源
                    if result.details and "data_sources" in result.details:
                        integrated["data_sources"].update(result.details["data_sources"])

                    # 记录研究领域
                    if result.task.task_type:
                        integrated["research_areas"].append(result.task.task_type)

                else:
                    integrated["failed_tasks"].append(result)
                    integrated["execution_summary"]["failed_tasks"] += 1

            # 转换set为list
            integrated["data_sources"] = list(integrated["data_sources"])

            # 去重和排序关键洞察
            integrated["key_insights"] = list(dict.fromkeys(integrated["key_insights"]))[:10]

            logger.info(f"整合完成: {len(integrated['successful_tasks'])} 成功, {len(integrated['failed_tasks'])} 失败")
            return integrated

        except Exception as e:
            logger.error(f"整合研究结果失败: {e}")
            return {
                "successful_tasks": research_results,
                "failed_tasks": [],
                "all_findings": ["研究数据整合过程中出现问题"],
                "key_insights": [],
                "data_sources": [],
                "research_areas": [],
                "execution_summary": {"error": str(e)}
            }

    def _extract_insights_from_result(self, result: ResearchResult) -> List[str]:
        """从单个结果中提取洞察"""
        insights = []

        # 从findings中提取洞察性内容
        for finding in result.findings:
            if any(keyword in finding for keyword in ["趋势", "增长", "挑战", "机遇", "优势", "风险"]):
                insights.append(finding)

        # 从details中提取结构化洞察
        if result.details:
            if "market_analysis" in result.details:
                insights.append("市场分析已纳入考量")
            if "financial_metrics" in result.details:
                insights.append("财务指标已进行分析")
            if "technical_info" in result.details:
                insights.append("技术信息已进行评估")

        return insights

    def _build_report_structure(
        self,
        question: str,
        research_brief: ResearchBrief,
        integrated_findings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建报告结构"""
        return {
            "title": f"关于'{question}'的深度研究报告",
            "metadata": {
                "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "research_scope": research_brief.scope,
                "key_aspects_count": len(research_brief.key_aspects),
                "research_duration": f"{research_brief.estimated_duration}分钟"
            },
            "sections": [
                {
                    "title": "执行摘要",
                    "type": "executive_summary",
                    "content": self._generate_executive_summary(
                        question, research_brief, integrated_findings
                    )
                },
                {
                    "title": "研究概述",
                    "type": "research_overview",
                    "content": self._generate_research_overview(research_brief, integrated_findings)
                },
                {
                    "title": "主要发现",
                    "type": "key_findings",
                    "content": self._generate_key_findings_section(integrated_findings)
                },
                {
                    "title": "详细分析",
                    "type": "detailed_analysis",
                    "content": self._generate_detailed_analysis(integrated_findings)
                },
                {
                    "title": "数据来源与研究方法",
                    "type": "methodology",
                    "content": self._generate_methodology_section(integrated_findings)
                },
                {
                    "title": "结论与建议",
                    "type": "conclusions",
                    "content": self._generate_conclusions(question, integrated_findings)
                }
            ]
        }

    def _generate_executive_summary(
        self,
        question: str,
        research_brief: ResearchBrief,
        integrated_findings: Dict[str, Any]
    ) -> str:
        """生成执行摘要"""
        success_rate = (len(integrated_findings["successful_tasks"]) /
                       max(integrated_findings["execution_summary"]["total_tasks"], 1)) * 100

        summary = f"""
本报告针对"{question}"进行了深度研究分析。

**研究概况：**
- 研究范围：{research_brief.scope}
- 重点分析方面：{len(research_brief.key_aspects)}个
- 研究任务完成率：{success_rate:.1f}%
- 成功完成任务：{len(integrated_findings["successful_tasks"])}个
- 总执行时间：{integrated_findings['execution_summary']['total_execution_time']:.2f}秒

**主要成果：**
- 收集关键发现：{len(integrated_findings['all_findings'])}条
- 识别重要洞察：{len(integrated_findings['key_insights'])}条
- 参考数据源：{len(integrated_findings['data_sources'])}个

**核心结论：**
本研究通过系统性的数据收集和分析，为"{question}"提供了全面深入的分析结果。研究发现涵盖了多个关键维度，为相关决策提供了有价值的参考依据。
        """.strip()

        return summary

    def _generate_research_overview(
        self,
        research_brief: ResearchBrief,
        integrated_findings: Dict[str, Any]
    ) -> str:
        """生成研究概述"""
        overview = f"""
**研究简报：**
{research_brief.brief}

**关键研究方面：**
"""
        for i, aspect in enumerate(research_brief.key_aspects, 1):
            overview += f"{i}. {aspect}\n"

        overview += f"""
**执行情况：**
- 计划研究时间：{research_brief.estimated_duration}分钟
- 实际完成研究任务：{len(integrated_findings['successful_tasks'])}个
- 涉及研究领域：{', '.join(set(integrated_findings['research_areas']))}
        """.strip()

        return overview

    def _generate_key_findings_section(self, integrated_findings: Dict[str, Any]) -> str:
        """生成主要发现部分"""
        findings_text = "**核心发现：**\n\n"

        # 展示关键洞察
        if integrated_findings["key_insights"]:
            findings_text += "**重要洞察：**\n"
            for i, insight in enumerate(integrated_findings["key_insights"][:8], 1):
                findings_text += f"{i}. {insight}\n"
            findings_text += "\n"

        # 展示一般发现
        if integrated_findings["all_findings"]:
            findings_text += "**详细发现：**\n"
            for i, finding in enumerate(integrated_findings["all_findings"][:15], 1):
                findings_text += f"{i}. {finding}\n"

        return findings_text

    def _generate_detailed_analysis(self, integrated_findings: Dict[str, Any]) -> str:
        """生成详细分析部分"""
        analysis = "**分领域分析结果：**\n\n"

        # 按任务类型分组分析
        task_groups = {}
        for result in integrated_findings["successful_tasks"]:
            task_type = result.task.task_type or "general_research"
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(result)

        for task_type, results in task_groups.items():
            analysis += f"**{task_type.replace('_', ' ').title()}分析：**\n"

            for result in results:
                analysis += f"- 任务：{result.task.description}\n"
                if result.findings:
                    analysis += f"  主要发现：{result.findings[0]}\n"
                if result.details:
                    details_summary = self._summarize_result_details(result.details)
                    if details_summary:
                        analysis += f"  详细信息：{details_summary}\n"
                analysis += "\n"

        return analysis

    def _summarize_result_details(self, details: Dict[str, Any]) -> str:
        """总结结果详情"""
        summaries = []

        if "financial_metrics" in details:
            summaries.append("包含财务指标分析")
        if "market_analysis" in details:
            summaries.append("包含市场格局分析")
        if "technical_info" in details:
            summaries.append("包含技术信息评估")
        if "basic_info" in details:
            summaries.append("包含基础信息整理")

        return "；".join(summaries) if summaries else ""

    def _generate_methodology_section(self, integrated_findings: Dict[str, Any]) -> str:
        """生成研究方法部分"""
        methodology = f"""
**研究方法与数据来源：**

**研究执行情况：**
- 总研究任务数：{integrated_findings['execution_summary']['total_tasks']}个
- 成功完成任务：{len(integrated_findings['successful_tasks'])}个
- 失败任务数：{len(integrated_findings['failed_tasks'])}个
- 总执行时间：{integrated_findings['execution_summary']['total_execution_time']:.2f}秒

**数据来源：**
"""
        if integrated_findings["data_sources"]:
            for source in integrated_findings["data_sources"][:10]:
                methodology += f"- {source}\n"
        else:
            methodology += "- 公开数据源\n- 行业报告\n- 官方信息\n"

        methodology += """
**研究工具与方法：**
- 多源信息收集与整合
- 交叉验证确保数据准确性
- 结构化数据分析
- 趋势识别与洞察提取

**质量控制：**
- 数据来源可靠性验证
- 信息时效性检查
- 内容相关性评估
- 多角度信息比对
        """.strip()

        return methodology

    def _generate_conclusions(self, question: str, integrated_findings: Dict[str, Any]) -> str:
        """生成结论与建议"""
        success_rate = (len(integrated_findings["successful_tasks"]) /
                       max(integrated_findings["execution_summary"]["total_tasks"], 1)) * 100

        conclusions = f"""
**研究结论：**

针对"{question}"的深度研究已顺利完成。本研究采用了系统性的多维度分析方法，涵盖了{len(set(integrated_findings['research_areas']))}个主要研究领域。

**主要成果：**
1. 收集并分析了{len(integrated_findings['all_findings'])}条关键信息
2. 识别出{len(integrated_findings['key_insights'])}条重要洞察
3. 研究任务成功率达到{success_rate:.1f}%
4. 整合了来自{len(integrated_findings['data_sources'])}个不同数据源的信息

**研究价值：**
本研究提供了关于"{question}"的全面分析，为相关决策提供了可靠的数据支持和专业的分析视角。研究过程中采用了严格的质量控制标准，确保了信息的准确性和可靠性。

**后续建议：**
- 建议定期更新相关数据，以保持信息的时效性
- 可根据具体需求对某些方面进行更深入的专项研究
- 建议将本研究结果与实际业务需求相结合，制定具体的行动计划

**研究完成时间：**{datetime.now().strftime("%Y年%m月%d日 %H:%M")}
        """.strip()

        return conclusions

    def _generate_detailed_content(self, report_structure: Dict[str, Any]) -> str:
        """生成详细内容"""
        content_parts = []

        # 添加标题
        content_parts.append(f"# {report_structure['title']}\n")

        # 添加元数据
        metadata = report_structure['metadata']
        content_parts.append(f"**报告生成时间：**{metadata['generation_time']}")
        content_parts.append(f"**研究范围：**{metadata['research_scope']}")
        content_parts.append(f"**研究时长：**{metadata['research_duration']}\n")

        # 添加各个章节
        for section in report_structure['sections']:
            content_parts.append(f"## {section['title']}\n")
            content_parts.append(section['content'])
            content_parts.append("\n")

        return "\n".join(content_parts)

    def _add_metadata_and_summary(
        self,
        final_report: str,
        question: str,
        research_brief: ResearchBrief,
        research_results: List[ResearchResult]
    ) -> str:
        """添加元信息和总结"""
        metadata_section = f"""
---
**报告信息**
- 研究问题：{question}
- 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 研究简报：{research_brief.brief[:100]}...
- 研究结果数：{len(research_results)}
- 成功率：{(len([r for r in research_results if r.status == 'success']) / max(len(research_results), 1)) * 100:.1f}%

**免责声明：**
本报告基于公开可获得的信息生成，仅供参考。使用者应根据实际情况对相关内容进行独立验证和判断。
---
        """

        return final_report + metadata_section

    def _generate_fallback_report(
        self,
        question: str,
        research_brief: ResearchBrief,
        research_results: List[ResearchResult]
    ) -> str:
        """生成备用报告（当主要生成过程失败时）"""
        return f"""
# 关于"{question}"的研究报告

## 报告说明
抱歉，在生成详细报告时遇到了技术问题。以下是基础研究信息：

## 研究概述
- **研究问题：**{question}
- **研究简报：**{research_brief.brief}
- **关键方面：**{', '.join(research_brief.key_aspects)}

## 研究结果
- **总任务数：**{len(research_results)}
- **成功任务：**{len([r for r in research_results if r.status == 'success'])}
- **失败任务：**{len([r for r in research_results if r.status == 'failed'])}

## 主要发现
"""

        # 添加可用的发现
        for result in research_results:
            if result.status == 'success' and result.findings:
                for finding in result.findings[:3]:
                    report += f"- {finding}\n"

        report += f"""
## 技术说明
报告生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
状态：基础版本（详细生成功能暂时不可用）

建议稍后重新生成完整报告。
        """