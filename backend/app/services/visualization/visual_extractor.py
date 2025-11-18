"""
AI数据提取器：从报告中识别可视化数据
"""
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from .chart_generator import ChartData
import logging

logger = logging.getLogger(__name__)


class ChartList(BaseModel):
    """图表列表"""
    charts: List[ChartData]


class VisualDataExtractor:
    """从研究报告中提取可视化数据"""
    
    def __init__(self, model):
        self.model = model
    
    async def extract(self, report: str) -> List[ChartData]:
        """
        提取报告中的可视化数据
        
        Args:
            report: Markdown格式的研究报告
            
        Returns:
            图表数据列表
        """
        extraction_prompt = """你是数据可视化专家。分析以下研究报告，识别所有可以可视化的数字数据。

**识别规则**：
1. 数字对比（2个以上数据点）→ 柱状图(bar)
2. 时间序列/趋势变化 → 折线图(line)
3. 占比/百分比分布 → 饼图(pie)
4. 多维度性能对比 → 雷达图(radar)
5. 相关性分析 → 散点图(scatter)

**研究报告**：
{report}

**输出格式**：请严格按照以下JSON格式输出，不要有任何额外文字：
```json
{{
  "charts": [
    {{
      "type": "bar",
      "title": "图表标题（简短明确）",
      "labels": ["标签1", "标签2", "标签3"],
      "datasets": [
        {{
          "label": "数据集名称",
          "data": [100, 200, 150]
        }}
      ]
    }}
  ]
}}
```

**重要**：
- 只输出JSON，不要有任何解释文字
- 如果没有数据，输出 {{"charts": []}}
- 数字必须是数值类型（不要带单位）
- labels和data长度必须一致
- 每个图表至少2个数据点
"""
        
        try:
            # 调用AI模型获取JSON响应
            response = await self.model.ainvoke([
                SystemMessage(content="你是数据可视化专家。请仔细分析报告中的数字数据，输出JSON格式的图表配置。"),
                HumanMessage(content=extraction_prompt.format(report=report))
            ])
            
            # 获取响应内容
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"[VISUAL] AI响应内容（前500字符）: {content[:500]}...")
            
            # 完整内容记录到DEBUG级别
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[VISUAL] AI完整响应:\n{content}")
            
            # 提取JSON部分（可能包裹在```json...```中）
            import re
            import json
            
            # 尝试提取JSON块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            elif content.strip().startswith('{'):
                json_str = content.strip()
            else:
                # 尝试查找第一个{到最后一个}
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                else:
                    logger.warning("[VISUAL] 无法从响应中提取JSON")
                    return []
            
            # 解析JSON
            data = json.loads(json_str)
            charts_data = data.get('charts', [])
            
            # 转换为ChartData对象
            charts = []
            for chart_dict in charts_data:
                try:
                    chart = ChartData(**chart_dict)
                    charts.append(chart)
                except Exception as e:
                    logger.warning(f"[VISUAL] 跳过无效图表: {e}")
                    continue
            
            logger.info(f"[VISUAL] 从报告中提取到 {len(charts)} 个图表")
            return charts
            
        except Exception as e:
            if "JSONDecodeError" in str(type(e)):
                logger.error(f"[VISUAL] JSON解析失败: {e}")
                logger.debug(f"[VISUAL] 原始内容: {content}")
            else:
                logger.error(f"[VISUAL] AI提取失败: {e}", exc_info=True)
            return []

