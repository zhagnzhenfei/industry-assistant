"""
图表工厂：智能选择引擎
"""
from typing import List
from .chart_engine import ChartEngine, QuickChartEngine, MatplotlibEngine
from .chart_generator import ChartData
from .chart_storage import ChartStorage, FileSystemStorage
from configs.visualization_config import get_visualization_settings
import logging

logger = logging.getLogger(__name__)


class ChartFactory:
    """图表工厂：智能选择引擎"""
    
    def __init__(self, storage: ChartStorage = None, base_url: str = None):
        settings = get_visualization_settings()
        
        self.storage = storage or FileSystemStorage(settings.CHART_STORAGE_DIR)
        self.base_url = base_url or settings.base_url
        
        # 引擎优先级：QuickChart > Matplotlib
        self.engines: List[ChartEngine] = [
            QuickChartEngine(),
            MatplotlibEngine(self.storage, self.base_url)  # 兜底引擎
        ]
    
    async def generate_chart(self, chart_data: ChartData) -> str:
        """
        生成图表，返回Markdown语法
        
        Returns:
            "![title](url)"
        """
        for engine in self.engines:
            if engine.can_handle(chart_data):
                try:
                    url, fmt = await engine.generate(chart_data)
                    
                    # 记录使用的引擎
                    engine_name = engine.__class__.__name__
                    logger.info(f"[CHART] {chart_data.title} → {engine_name} → {url}")
                    
                    return chart_data.to_markdown(url)
                    
                except Exception as e:
                    logger.error(f"[CHART] {engine.__class__.__name__} failed: {e}", exc_info=True)
                    continue  # 尝试下一个引擎
        
        # 所有引擎都失败
        logger.error(f"[CHART] 所有引擎都失败: {chart_data.title}")
        return f"\n> ⚠️ 图表生成失败：{chart_data.title}\n"

