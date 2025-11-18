"""
图表引擎实现
"""
from abc import ABC, abstractmethod
from typing import Tuple
from .chart_generator import ChartData
from .chart_storage import ChartStorage
import logging

logger = logging.getLogger(__name__)


class ChartEngine(ABC):
    """图表引擎抽象基类"""
    
    @abstractmethod
    async def generate(self, chart_data: ChartData) -> Tuple[str, str]:
        """
        生成图表
        
        Returns:
            (url_or_path, format)  # ("https://...", "url") 或 ("chart_id", "id")
        """
        pass
    
    @abstractmethod
    def can_handle(self, chart_data: ChartData) -> bool:
        """判断是否能处理该图表"""
        pass


class QuickChartEngine(ChartEngine):
    """QuickChart在线引擎（简单快速）"""
    
    def can_handle(self, chart_data: ChartData) -> bool:
        """QuickChart支持的基础图表"""
        supported_types = ["bar", "line", "pie", "radar", "scatter"]
        
        # 复杂度判断
        is_simple = (
            chart_data.type in supported_types and
            len(chart_data.datasets) <= 3 and  # 不超过3个数据集
            len(chart_data.labels) <= 20  # 不超过20个标签
        )
        return is_simple
    
    async def generate(self, chart_data: ChartData) -> Tuple[str, str]:
        """生成QuickChart URL"""
        url = chart_data.to_url(width=700, height=400)
        return (url, "url")


class MatplotlibEngine(ChartEngine):
    """Matplotlib本地引擎（复杂图表）"""
    
    def __init__(self, storage: ChartStorage, base_url: str):
        self.storage = storage
        self.base_url = base_url
    
    def can_handle(self, chart_data: ChartData) -> bool:
        """Matplotlib可以处理所有图表"""
        return True
    
    async def generate(self, chart_data: ChartData) -> Tuple[str, str]:
        """生成Matplotlib图表并保存"""
        import matplotlib
        matplotlib.use('Agg')  # 无GUI后端
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        # 设置中文字体
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            logger.warning("无法设置中文字体，可能显示为方块")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 根据类型绘制
        if chart_data.type == "bar":
            self._draw_bar(ax, chart_data)
        elif chart_data.type == "line":
            self._draw_line(ax, chart_data)
        elif chart_data.type == "pie":
            self._draw_pie(ax, chart_data)
        elif chart_data.type == "radar":
            self._draw_radar(ax, chart_data)
        elif chart_data.type == "scatter":
            self._draw_scatter(ax, chart_data)
        
        ax.set_title(chart_data.title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # 保存到内存
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 保存到存储
        buffer.seek(0)
        chart_id = await self.storage.save(buffer.read(), format="png")
        
        # 返回完整URL
        full_url = f"{self.base_url}/api/charts/{chart_id}"
        return (full_url, "url")
    
    def _draw_bar(self, ax, chart_data: ChartData):
        """绘制柱状图"""
        x = range(len(chart_data.labels))
        width = 0.8 / len(chart_data.datasets)
        
        for i, dataset in enumerate(chart_data.datasets):
            offset = (i - len(chart_data.datasets)/2) * width + width/2
            ax.bar([p + offset for p in x], dataset.data, width, 
                   label=dataset.label, alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(chart_data.labels, rotation=45, ha='right')
        if len(chart_data.datasets) > 1:
            ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    def _draw_line(self, ax, chart_data: ChartData):
        """绘制折线图"""
        for dataset in chart_data.datasets:
            ax.plot(chart_data.labels, dataset.data, 
                   marker='o', label=dataset.label, linewidth=2)
        if len(chart_data.datasets) > 1:
            ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _draw_pie(self, ax, chart_data: ChartData):
        """绘制饼图"""
        # 饼图只用第一个dataset
        dataset = chart_data.datasets[0]
        ax.pie(dataset.data, labels=chart_data.labels, autopct='%1.1f%%',
               startangle=90)
        ax.axis('equal')
    
    def _draw_radar(self, ax, chart_data: ChartData):
        """绘制雷达图"""
        import numpy as np
        
        # 计算角度
        num_vars = len(chart_data.labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        
        # 关闭图形
        for dataset in chart_data.datasets:
            values = dataset.data + [dataset.data[0]]
            angles_plot = angles + [angles[0]]
            ax.plot(angles_plot, values, 'o-', linewidth=2, label=dataset.label)
            ax.fill(angles_plot, values, alpha=0.25)
        
        ax.set_xticks(angles)
        ax.set_xticklabels(chart_data.labels)
        if len(chart_data.datasets) > 1:
            ax.legend()
    
    def _draw_scatter(self, ax, chart_data: ChartData):
        """绘制散点图"""
        # 散点图：假设datasets[0]是x，datasets[1]是y
        if len(chart_data.datasets) >= 2:
            ax.scatter(chart_data.datasets[0].data, 
                      chart_data.datasets[1].data, 
                      alpha=0.6, s=50)
            ax.set_xlabel(chart_data.datasets[0].label)
            ax.set_ylabel(chart_data.datasets[1].label)
        ax.grid(True, alpha=0.3)

