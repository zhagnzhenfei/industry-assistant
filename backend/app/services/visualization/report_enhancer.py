"""
报告增强器：为Markdown报告添加可视化
"""
from typing import List
from .visual_extractor import VisualDataExtractor
from .chart_factory import ChartFactory
from .chart_generator import ChartData
import time
import logging

logger = logging.getLogger(__name__)


class ReportEnhancer:
    """报告增强器：添加可视化"""
    
    def __init__(self, model, base_url: str = None):
        self.extractor = VisualDataExtractor(model)
        self.factory = ChartFactory(base_url=base_url)
    
    async def enhance(self, markdown_report: str) -> dict:
        """
        增强Markdown报告，添加可视化
        
        Args:
            markdown_report: 原始Markdown报告
            
        Returns:
            {
                "enhanced_report": "增强后的报告",
                "chart_count": 图表数量,
                "charts_metadata": [...],
                "processing_time": 处理时间
            }
        """
        start_time = time.time()
        
        # 1. AI识别可视化数据
        logger.info("[ENHANCE] 🔍 识别可视化数据...")
        charts = await self.extractor.extract(markdown_report)
        logger.info(f"[ENHANCE] ✓ 识别到 {len(charts)} 个图表")
        
        if not charts:
            return {
                "enhanced_report": markdown_report,
                "chart_count": 0,
                "charts_metadata": [],
                "processing_time": time.time() - start_time
            }
        
        # 2. 生成图表
        logger.info("[ENHANCE] 🎨 生成图表...")
        chart_markdowns = []
        charts_metadata = []
        
        for i, chart in enumerate(charts, 1):
            chart_md = await self.factory.generate_chart(chart)
            chart_markdowns.append(chart_md)
            
            charts_metadata.append({
                "index": i,
                "title": chart.title,
                "type": chart.type,
                "data_points": len(chart.labels)
            })
        
        # 3. 智能插入图表到报告
        enhanced_report = await self._insert_charts(
            markdown_report, 
            charts, 
            chart_markdowns
        )
        
        processing_time = time.time() - start_time
        logger.info(f"[ENHANCE] ✓ 可视化完成，耗时 {processing_time:.2f}秒")
        
        return {
            "enhanced_report": enhanced_report,
            "chart_count": len(charts),
            "charts_metadata": charts_metadata,
            "processing_time": processing_time
        }
    
    async def _insert_charts(
        self, 
        report: str, 
        charts: List[ChartData], 
        chart_markdowns: List[str]
    ) -> str:
        """智能插入图表到报告的合适位置"""
        
        if not chart_markdowns:
            return report
        
        # 使用AI重新组织报告，将图表插入到合适位置
        reorganization_prompt = f"""
请重新组织以下研究报告，将图表智能地插入到相关的文本段落中，而不是放在最后。

要求：
1. 保持原报告的结构和内容完整性
2. 将每个图表插入到最相关的段落附近
3. 为图表添加简短的说明文字（避免"为了更直观地展示"等AI解释性语言）
4. 确保图表与上下文自然衔接，过渡要自然流畅
5. 图表使用 [CHART_PLACEHOLDER_X] 作为占位符
6. 过渡文字要简洁自然，如"下图展示了..."、"从数据可以看出..."等

原报告：
{report}

图表信息：
{self._format_charts_info(charts, chart_markdowns)}

请重新组织报告：
"""
        
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            logger.info(f"[ENHANCE] 🔄 开始智能插入：调用AI重新组织报告...")
            
            response = await self.extractor.model.ainvoke([
                SystemMessage(content="你是专业的技术写作助手，擅长将数据可视化自然地集成到报告中。"),
                HumanMessage(content=reorganization_prompt)
            ])
            
            reorganized_report = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"[ENHANCE] 📝 AI返回报告长度: {len(reorganized_report)} 字符")
            
            # 检查AI是否使用了占位符
            placeholders_found = []
            for i in range(1, len(chart_markdowns) + 1):
                placeholder = f"[CHART_PLACEHOLDER_{i}]"
                if placeholder in reorganized_report:
                    placeholders_found.append(i)
            
            logger.info(f"[ENHANCE] 🔍 找到占位符: {placeholders_found} / {len(chart_markdowns)}")
            
            # 替换占位符为实际图表
            replacement_count = 0
            for i, chart_md in enumerate(chart_markdowns, 1):
                placeholder = f"[CHART_PLACEHOLDER_{i}]"
                if placeholder in reorganized_report:
                    reorganized_report = reorganized_report.replace(placeholder, chart_md)
                    replacement_count += 1
            
            logger.info(f"[ENHANCE] ✓ 智能插入完成: 替换了 {replacement_count}/{len(chart_markdowns)} 个占位符")
            
            # 如果没有找到任何占位符，说明AI没有按照要求使用占位符
            if replacement_count == 0:
                logger.warning(f"[ENHANCE] ⚠️ AI未使用占位符，降级到默认方式")
                return self._insert_charts_fallback(report, charts, chart_markdowns)
            
            return reorganized_report
            
        except Exception as e:
            logger.warning(f"[ENHANCE] ❌ 智能插入失败，使用默认方式: {e}")
            # 降级到默认方式
            return self._insert_charts_fallback(report, charts, chart_markdowns)
    
    def _format_charts_info(self, charts: List[ChartData], chart_markdowns: List[str]) -> str:
        """格式化图表信息"""
        info = []
        for i, (chart, chart_md) in enumerate(zip(charts, chart_markdowns), 1):
            info.append(f"""
图表 {i}: {chart.title}
类型: {chart.type}
标签: {', '.join(chart.labels)}
数据集: {', '.join([d.label for d in chart.datasets])}
占位符: [CHART_PLACEHOLDER_{i}]
""")
        return "\n".join(info)
    
    def _insert_charts_fallback(
        self, 
        report: str, 
        charts: List[ChartData], 
        chart_markdowns: List[str]
    ) -> str:
        """降级方案：在报告末尾插入图表"""
        
        enhanced = report
        
        if chart_markdowns:
            enhanced += "\n\n---\n\n## 📊 数据可视化\n\n"
            
            for i, (chart, chart_md) in enumerate(zip(charts, chart_markdowns), 1):
                enhanced += f"\n### {i}. {chart.title}\n\n"
                enhanced += f"{chart_md}\n\n"
        
        return enhanced

