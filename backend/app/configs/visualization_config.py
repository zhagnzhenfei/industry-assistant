"""
图表可视化配置
"""
import os
from functools import lru_cache


class VisualizationSettings:
    """可视化配置"""
    
    def __init__(self):
        self.API_HOST = os.getenv("API_HOST", "localhost")
        self.API_PORT = int(os.getenv("API_PORT", "8001"))
        self.API_SCHEME = os.getenv("API_SCHEME", "http")
        self.CHART_STORAGE_DIR = os.getenv("CHART_STORAGE_DIR", "./data/charts")
    
    @property
    def base_url(self) -> str:
        """生成完整的BASE_URL"""
        return f"{self.API_SCHEME}://{self.API_HOST}:{self.API_PORT}"


@lru_cache()
def get_visualization_settings() -> VisualizationSettings:
    """获取可视化配置单例"""
    return VisualizationSettings()

