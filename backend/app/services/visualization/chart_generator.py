"""
图表数据模型和生成器
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import json
import urllib.parse


class ChartDataset(BaseModel):
    """图表数据集"""
    label: str = Field(description="数据集标签")
    data: List[float] = Field(description="数据值列表")
    backgroundColor: Optional[str] = Field(default=None, description="背景色")
    borderColor: Optional[str] = Field(default=None, description="边框色")


class ChartData(BaseModel):
    """图表数据模型"""
    type: Literal["bar", "line", "pie", "radar", "scatter"] = Field(description="图表类型")
    title: str = Field(description="图表标题")
    labels: List[str] = Field(description="标签列表")
    datasets: List[ChartDataset] = Field(description="数据集列表")
    
    def to_quickchart_config(self) -> dict:
        """转换为QuickChart配置"""
        config = {
            "type": self.type,
            "data": {
                "labels": self.labels,
                "datasets": [d.dict(exclude_none=True) for d in self.datasets]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": self.title,
                    "fontSize": 16
                },
                "plugins": {
                    "datalabels": {
                        "display": True,
                        "anchor": "end",
                        "align": "top"
                    }
                },
                "legend": {
                    "display": len(self.datasets) > 1
                }
            }
        }
        
        # 特定类型的配置
        if self.type in ["bar", "line"]:
            config["options"]["scales"] = {
                "yAxes": [{
                    "ticks": {"beginAtZero": True}
                }]
            }
        
        return config
    
    def to_url(self, width: int = 700, height: int = 400) -> str:
        """生成QuickChart URL"""
        config = self.to_quickchart_config()
        encoded = urllib.parse.quote(json.dumps(config))
        url = f"https://quickchart.io/chart?w={width}&h={height}&c={encoded}"
        return url
    
    def to_markdown(self, url: str) -> str:
        """生成Markdown图片语法"""
        return f"![{self.title}]({url})"

